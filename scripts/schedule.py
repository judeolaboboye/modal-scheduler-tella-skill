#!/usr/bin/env python3
"""Schedule Tella videos to YouTube, YouTube Shorts, LinkedIn and X.

Tella's API posts straight away and has no schedule field. This puts posts in a queue
with a time; a small cloud job (Modal by default) posts each one when it is due.

  schedule.py accounts
        The social accounts connected in Tella (read-only check of your key).
  schedule.py add --video vid_xxx --to youtube_shorts,x --title "..." [--description "..."]
                  (--at "2026-10-12 14:30" | --random 08:00-21:30) [--date tomorrow]
                  [--privacy public|unlisted|private] [--subtitles] [--go]
        One video, one or more destinations.
  schedule.py plan batch.json [--date today|tomorrow|2026-10-12] [--window 08:00-21:30]
                  [--gap 45] [--go]
        Many videos in one day, at random times spread across the window.
  schedule.py status              what is scheduled / posted / failed, with post links
  schedule.py cancel <id> | --all
  schedule.py retry <id>          put a failed / missed post back, due now
  schedule.py pause | resume

add and plan only PREVIEW unless you pass --go. Times are in your timezone
(TELLA_SCHEDULE_TZ, e.g. Africa/Lagos; default: this computer's timezone).
"""
import argparse
import json
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tella_api  # noqa: E402
from stores import open_store  # noqa: E402

TZ = ZoneInfo(os.environ["TELLA_SCHEDULE_TZ"]) if os.environ.get("TELLA_SCHEDULE_TZ") else datetime.now().astimezone().tzinfo
MIN_LEAD = timedelta(minutes=15)


def now():
    return datetime.now(TZ)


def due(i):
    return datetime.fromisoformat(i["dueAt"]).astimezone(TZ)


def the_day(arg):
    if arg in (None, "today"):
        return now().date()
    return now().date() + timedelta(days=1) if arg == "tomorrow" else date.fromisoformat(arg)


def window(arg, d):
    """'08:00-21:30' on day d -> (start, end), start never earlier than a few minutes from now."""
    a, b = (datetime.combine(d, datetime.strptime(t, "%H:%M").time(), TZ) for t in arg.split("-"))
    return max(a, now() + MIN_LEAD), b


def random_times(k, start, end, gap):
    """k random times, one per equal slice of the window, at least `gap` apart. None if they don't fit."""
    if k < 1 or start >= end:
        return None
    slice_ = (end - start) / k
    if k > 1 and slice_ < gap:
        return None
    out, prev = [], None
    for j in range(k):
        lo, hi = start + slice_ * j, start + slice_ * (j + 1)
        if prev:
            lo = max(lo, prev + gap)
        prev = (lo + (hi - lo) * random.random()).replace(second=0, microsecond=0)
        out.append(prev)
    return out


def make(video, dest, t, title, description, privacy="public", subtitles=False, account=None):
    if dest not in tella_api.DESTINATIONS:
        sys.exit(f"'{dest}' is not something the Tella API can post to. Use: {', '.join(tella_api.DESTINATIONS)}")
    if not title:
        sys.exit("every post needs a title")
    return {"id": f"{video}-{dest}", "videoId": video, "destination": dest, "title": title,
            "description": description or "", "privacy": privacy, "subtitles": bool(subtitles), "accountId": account,
            "dueAt": t.astimezone(timezone.utc).isoformat(), "status": "scheduled"}


def show(items):
    if not items:
        return print("(nothing)")
    print(f"{'when':<17} {'destination':<15} {'status':<10} {'id':<44} link / note")
    for i in sorted(items, key=due):
        print(f"{due(i):%a %d %b %H:%M}  {i['destination']:<15} {i['status']:<10} {i['id']:<44} {i.get('url') or i.get('error') or i['title'][:40]}")


def commit(new, go):
    show(new)
    if not go:
        return print(f"\nPREVIEW ONLY, nothing scheduled ({len(new)} posts). Add --go to schedule.")
    store = open_store()
    for i in new:
        old = store.get(i["id"])
        if old and old["status"] not in ("failed", "missed", "cancelled"):
            print(f"  skipped, already {old['status']}: {i['id']}")
            continue
        store[i["id"]] = i
    print("\nSCHEDULED. Follow it with: schedule.py status")


def cmd_add(a):
    dests = a.to.split(",")
    d = the_day(a.date)
    if a.at:
        t = datetime.strptime(a.at, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
        if t < now():
            sys.exit("--at is in the past")
        times = [t] * len(dests)
    else:
        start, end = window(a.random or "08:00-21:30", d)
        if start >= end:
            sys.exit(f"Nothing left of that window on {d:%a %d %b}. Use --date tomorrow.")
        times = [random_times(1, start, end, timedelta(0))[0] for _ in dests]
    commit([make(a.video, dest, t, a.title, a.description, a.privacy, a.subtitles, a.account) for dest, t in zip(dests, times)], a.go)


def cmd_plan(a):
    posts = json.loads(Path(a.batch).read_text())["posts"]
    d = the_day(a.date)
    start, end = window(a.window, d)
    gap = timedelta(minutes=a.gap)
    new = []
    for dest in tella_api.DESTINATIONS:
        mine = [p for p in posts if dest in p["destinations"]]
        if not mine:
            continue
        times = random_times(len(mine), start, end, gap)
        if times is None:
            left = max(end - start, timedelta(0))
            sys.exit(f"{len(mine)} posts to {dest} don't fit on {d:%a %d %b}: they need {len(mine)} x {a.gap} min and "
                     f"only {left.seconds // 3600} h {left.seconds % 3600 // 60:02d} min of the window is left. "
                     "Use --date tomorrow, a smaller --gap, or fewer posts. Nothing was scheduled.")
        for p, t in zip(mine, times):
            o = p.get(dest, {})  # optional per-destination text
            new.append(make(p["videoId"], dest, t, o.get("title") or p.get("title"), o.get("description", p.get("description")),
                            o.get("privacy", p.get("privacy", "public")), p.get("subtitles"), o.get("accountId")))
    commit(new, a.go)


def cmd_status(a):
    store = open_store()
    if store.get("_paused"):
        print("PAUSED (schedule.py resume to restart)\n")
    show([v for k, v in store.items() if not k.startswith("_") and v["status"] != "cancelled"])


def cmd_cancel(a):
    store = open_store()
    for k, i in list(store.items()):
        if k.startswith("_") or not (a.all or k == a.id):
            continue
        if i["status"] in ("scheduled", "failed", "missed"):
            i["status"] = "cancelled"
            store[k] = i
            print("cancelled", k)
        elif i["status"] in ("sending", "sent"):
            print(f"{k}: Tella is already uploading it, too late to cancel")


def cmd_retry(a):
    store = open_store()
    i = store.get(a.id)
    if not i or i["status"] not in ("failed", "missed", "cancelled"):
        sys.exit(f"nothing to retry for {a.id}" + (f" (it is '{i['status']}')" if i else ""))
    i.update(status="scheduled", dueAt=datetime.now(timezone.utc).isoformat(), attempts=0)
    i.pop("error", None)
    store[a.id] = i
    print("back in the queue, due now:", a.id)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("accounts")
    p = sub.add_parser("add")
    p.add_argument("--video", required=True)
    p.add_argument("--to", required=True, help="comma list: youtube,youtube_shorts,linkedin,x")
    p.add_argument("--title", required=True)
    p.add_argument("--description")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--at", help='exact local time: "2026-10-12 14:30"')
    g.add_argument("--random", help="random time inside a window, e.g. 08:00-21:30")
    p.add_argument("--date", help="for --random: today (default), tomorrow or YYYY-MM-DD")
    p.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    p.add_argument("--subtitles", action="store_true", help="burn the Tella subtitles into the export")
    p.add_argument("--account", help="accountId from `accounts`, when several are connected")
    p.add_argument("--go", action="store_true")
    p = sub.add_parser("plan")
    p.add_argument("batch")
    p.add_argument("--date")
    p.add_argument("--window", default="08:00-21:30")
    p.add_argument("--gap", type=int, default=45, help="minutes between posts on the same destination")
    p.add_argument("--go", action="store_true")
    sub.add_parser("status")
    p = sub.add_parser("cancel")
    p.add_argument("id", nargs="?")
    p.add_argument("--all", action="store_true")
    sub.add_parser("retry").add_argument("id")
    sub.add_parser("pause")
    sub.add_parser("resume")
    a = ap.parse_args()
    if a.cmd == "accounts":
        for acc in tella_api.accounts():
            print(f"{'connected' if acc['connected'] else 'RECONNECT IN TELLA':<19} {', '.join(acc['destinations']):<26} {acc['name']}  ({acc['id']})")
        return
    if a.cmd in ("pause", "resume"):
        open_store()["_paused"] = a.cmd == "pause"
        return print("Scheduler paused." if a.cmd == "pause" else "Scheduler resumed.")
    if a.cmd == "cancel" and not (a.id or a.all):
        sys.exit("give an id or --all")
    {"add": cmd_add, "plan": cmd_plan, "status": cmd_status, "cancel": cmd_cancel, "retry": cmd_retry}[a.cmd](a)


if __name__ == "__main__":
    main()
