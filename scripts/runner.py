"""One pass over the queue: post what is due, follow up on what Tella is uploading.

Pure logic, no scheduler in here. Something has to call run() every few minutes:
modal_app.py (Modal cron) or run_once.py (GitHub Actions, cron, any other scheduler).

`store` is dict-like: item id -> item. Item statuses:
  scheduled -> sending -> sent -> posted | failed        (plus: missed, cancelled)
"""
from datetime import datetime, timedelta, timezone

import tella_api

CATCH_UP_GAP = timedelta(minutes=20)  # if posts pile up, space them out, never burst
TOO_LATE = timedelta(hours=6)         # later than this -> "missed", not posted at an odd hour


def _t(s):
    return datetime.fromisoformat(s)


def run(store, tella=tella_api, now=None):
    """Returns a list of log lines."""
    if store.get("_paused"):
        return ["paused"]
    now = now or datetime.now(timezone.utc)
    items = [v for k, v in store.items() if not k.startswith("_")]
    out = []

    def put(i):
        store[i["id"]] = i

    def find(i):
        for p in tella.publications(i["videoId"]):
            if p["destination"] == i["destination"] and (not i.get("accountId") or p.get("accountId") == i["accountId"]):
                return p
        return None

    def absorb(i, p):
        if p["status"] == "completed":
            i.update(status="posted", url=p.get("url"), postedAt=now.isoformat())
            out.append(f"POSTED {i['id']} {p.get('url')}")
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
