"""One pass over the queue: post what is due, follow up on what Tella is uploading.

Pure logic, no scheduler in here. Something has to call run() every few minutes:
modal_app.py (Modal cron) or run_once.py (GitHub Actions, cron, any other scheduler).

`store` is dict-like: item id -> item. Item statuses:
  scheduled -> sending -> sent -> posted | failed        (plus: missed, cancelled)
  limit = YouTube said "daily limit"; moved back to scheduled for just after the reset

Call refresh(store) on every tick too when the store is a Modal Dict (modal_app.py does).
"""
from datetime import datetime, timedelta, timezone

import tella_api

CATCH_UP_GAP = timedelta(minutes=20)  # if posts pile up, space them out, never burst
TOO_LATE = timedelta(hours=6)         # later than this -> "missed", not posted at an odd hour
REFRESH_EVERY = timedelta(hours=12)   # rewrite waiting posts so Modal never expires them (see refresh)
YOUTUBE = ("youtube", "youtube_shorts")


def _t(s):
    return datetime.fromisoformat(s)


def youtube_reset(now):
    """YouTube's daily upload limit resets at midnight Pacific time."""
    try:
        from zoneinfo import ZoneInfo
        pt = now.astimezone(ZoneInfo("America/Los_Angeles"))
    except Exception:
        pt = now.astimezone(timezone(timedelta(hours=-8)))
    return (pt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def is_daily_limit(err):
    return "daily limit" in str(err).lower()


def wait_for_reset(store, items, now, out):
    """YouTube said "daily limit": don't fail. Every waiting YouTube post due before the reset moves to
    10 minutes after it (same order; the normal 20-minute gap spaces them), and no attempts are made until then."""
    reset = youtube_reset(now) + timedelta(minutes=10)
    store["_youtube_limit_until"] = reset.isoformat()
    late = sorted((i for i in items if i["destination"] in YOUTUBE and i["status"] in ("scheduled", "limit")
                   and _t(i["dueAt"]) < reset), key=lambda i: i["dueAt"])
    for n, i in enumerate(late):
        i.setdefault("origDueAt", i["dueAt"])
        i.update(status="scheduled", dueAt=(reset + timedelta(seconds=n)).isoformat(),
                 note="YouTube daily limit: moved to just after the reset")
        i.pop("error", None)
        store[i["id"]] = i
    out.append(f"YOUTUBE DAILY LIMIT: {len(late)} post(s) moved to {reset.isoformat()}")


def refresh(store, now=None):
    """Modal deletes a Dict entry after 7 days with no read or write, and listing the queue doesn't count.
    Without this, every post scheduled more than a week ahead silently disappears. Every 12 hours, rewrite
    each waiting post that is more than 5 hours away (never one about to be published)."""
    now = now or datetime.now(timezone.utc)
    last = store.get("_refreshed")
    if last and now - _t(last) < REFRESH_EVERY:
        return []
    keep = {k: v for k, v in store.items() if not k.startswith("_") and v.get("status") == "scheduled"
            and _t(v["dueAt"]) - now > timedelta(hours=5)}
    store.update(keep)
    store["_refreshed"] = now.isoformat()
    return [f"refreshed {len(keep)} waiting posts (Modal drops entries untouched for 7 days)"]


def run(store, tella=tella_api, now=None):
    """Returns a list of log lines."""
    if store.get("_paused"):
        return ["paused"]
    now = now or datetime.now(timezone.utc)
    items = [v for k, v in store.items() if not k.startswith("_")]
    out = []

    def put(i):
        store[i["id"]] = i

    def find(i):  # the newest publication for this destination/account, never an older failed one
        mine = [p for p in tella.publications(i["videoId"])
                if p["destination"] == i["destination"] and (not i.get("accountId") or p.get("accountId") == i["accountId"])]
        return max(mine, key=lambda p: p.get("createdAt") or "") if mine else None

    def absorb(i, p):
        if p["status"] == "completed":
            i.update(status="posted", url=p.get("url"), postedAt=now.isoformat())
            out.append(f"POSTED {i['id']} {p.get('url')}")
        elif p["status"] == "failed" and i["destination"] in YOUTUBE and is_daily_limit(p.get("error")):
            i["status"] = "limit"
            put(i)
            wait_for_reset(store, items, now, out)
            return
        elif p["status"] == "failed":
            i.update(status="failed", error=str(p.get("error"))[:300])
            out.append(f"FAILED {i['id']} {i['error']}")
        else:
            i["status"] = "sent"
        put(i)

    for i in items:  # follow up on what Tella already has
        if i["status"] not in ("sent", "sending"):
            continue
        p = find(i)
        if p and (i["status"] == "sent" or p["status"] != "failed"):
            absorb(i, p)
        elif i["status"] == "sending" and now - _t(i["sendingAt"]) > timedelta(minutes=30):
            i["status"] = "scheduled"  # the publish never reached Tella; safe to try again
            put(i)

    for lane in sorted({(i["destination"], i.get("accountId") or "") for i in items}):
        mine = [i for i in items if (i["destination"], i.get("accountId") or "") == lane]
        if any(i["status"] in ("sent", "sending") for i in mine):
            continue  # Tella runs one publish per destination and account at a time
        until = store.get("_youtube_limit_until") if lane[0] in YOUTUBE else None
        if until and now < _t(until):
            continue  # YouTube's daily limit: wait for the reset instead of burning attempts
        last = [_t(i["sentAt"]) for i in mine if i.get("sentAt")]
        if last and now - max(last) < CATCH_UP_GAP:
            continue
        ready = sorted((i for i in mine if i["status"] == "scheduled" and _t(i["dueAt"]) <= now), key=lambda i: i["dueAt"])
        if not ready:
            continue
        i = ready[0]
        if now - _t(i["dueAt"]) > TOO_LATE:
            i.update(status="missed", error="more than 6 hours late, not posted")
            put(i)
            out.append(f"MISSED {i['id']}")
            continue
        p = find(i)
        if p and p["status"] in ("queued", "running", "completed"):
            out.append(f"{i['id']} is already on {i['destination']}, not posting again")
            absorb(i, p)
            continue
        i.update(status="sending", sendingAt=now.isoformat())
        put(i)  # written before the call, so a crash can never cause a double post
        try:
            tella.publish(i)
        except RuntimeError as e:
            if i["destination"] in YOUTUBE and is_daily_limit(e):
                i["status"] = "limit"
                put(i)
                wait_for_reset(store, items, now, out)
                continue
            i["attempts"] = i.get("attempts", 0) + 1
            if i["attempts"] >= 2 or "Tella 403" in str(e):
                i.update(status="failed", error=str(e)[:300])
            else:
                i["status"] = "scheduled"
            put(i)
            out.append(f"publish error {i['id']} (try {i['attempts']}): {e}")
            continue
        i.update(status="sent", sentAt=now.isoformat())
        put(i)
        out.append(f"SENT {i['id']} -> {i['destination']}")
    return out
