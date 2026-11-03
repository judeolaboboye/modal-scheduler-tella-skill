# Tella Schedule — a scheduler skill for Tella (Modal, free)

Schedule your [Tella](https://www.tella.com) videos to go out later on **YouTube,
YouTube Shorts, LinkedIn, X, Instagram and Facebook**, without opening Tella for each one.

Tella can publish a video to your social accounts. Its own scheduling only reaches 30
days ahead, and it posts the export made when you scheduled it. This skill keeps your
own queue with no limit on how far ahead, spaces posts out, and never posts a video
twice to the same place.

This skill adds the missing piece. Your AI agent (Claude Code, Codex, Antigravity,
Cursor…) puts each post in a queue with a time. A tiny cloud job on
[Modal](https://modal.com) checks the queue every 10 minutes and tells Tella to publish
whatever is due. Your computer, Tella and the chat can all be closed.

```
you: "schedule these 7 clips across today at random times"
agent → schedule.py plan batch.json        (shows you the times)
you: "yes"
agent → schedule.py plan batch.json --go   (posts are queued in the cloud)
                 │
     Modal cron, every 10 min ──► Tella API ──► YouTube / Shorts / LinkedIn / X / Instagram / Facebook
```

## What it does not do

This only schedules what Tella's API can publish. Be clear on this before you install:

| Platform | Works? | Why not |
|---|---|---|
| YouTube, YouTube Shorts, LinkedIn, X | Yes | |
| Instagram (post, reel, story), Facebook (post, story) | Yes | Through one Facebook connection in Tella; Instagram must be a Business/Creator account linked to a Page |
| **TikTok** | No | TikTok requires its consent form on every post, so Tella only posts to TikTok from inside the Tella app. No outside tool can do it for you. |
| **Threads, Substack** | No | Tella does not publish to them at all. |

For those you still use the Tella app (TikTok) or a separate tool such as Buffer
(Threads, Substack). This skill does not replace that.

It also does not edit, cut or caption videos. The video must be finished in Tella.

**New to this? The full step-by-step guide, from creating your Modal account to the
GitHub Actions / cron / launchd / Windows alternatives, is [SETUP_GUIDE.md](SETUP_GUIDE.md).**

## Requirements

1. **Tella** with API access: an API key from *Settings → API Keys*, and your social
   accounts connected in *Settings → Connections*.
2. **An AI agent that can run terminal commands** on your computer: Claude Code, Codex
   CLI, Antigravity / Gemini CLI, Cursor, or similar. (A plain chat window such as
   ChatGPT in the browser cannot run it. You can also run the commands yourself.)
3. **A scheduler your agent can reach.** Default is **Modal** (free account, free
   monthly credit): `pip install modal`, then `modal setup` once to log in.
   Alternatives are below.
4. **Python 3.9 or newer.** No other packages.

## Install

```bash
# Claude Code
git clone https://github.com/judeolaboboye/modal-scheduler-tella-skill ~/.claude/skills/tella-schedule

# Any other agent: clone it anywhere and tell the agent to read SKILL.md
git clone https://github.com/judeolaboboye/modal-scheduler-tella-skill
```

## Set up (once, about 5 minutes)

1. **Tella key.** In Tella: *Settings → API Keys → Create key*. Then:
   ```bash
   cd ~/.claude/skills/tella-schedule
   cp .env.example .env        # paste the key after TELLA_API_KEY=
   ```
2. **Check it.** This lists the accounts Tella can post to:
   ```bash
   python scripts/schedule.py accounts
   ```
3. **Turn the scheduler on.** Run this yourself (it stores your key as a Modal secret
   and starts a cron job on your Modal account):
   ```bash
   scripts/deploy_modal.sh
   ```
4. **Test with one private post** before trusting it with public ones:
   ```bash
   python scripts/schedule.py add --video vid_xxx --to youtube --title "Scheduler test" \
     --privacy private --random 00:00-23:59 --go
   python scripts/schedule.py status      # run again after ~15 minutes
   ```

## Use it

Just ask your agent:

- "Schedule this Tella video to YouTube Shorts and X tomorrow at 2:30 pm."
- "Post these 7 clips today at random times, at least 45 minutes apart."
- "What went out today?" / "Cancel the LinkedIn one." / "Pause the scheduler."

Or run it yourself:

```bash
# one video, exact time
python scripts/schedule.py add --video vid_xxx --to youtube_shorts,x \
  --title "Title" --description "Post text" --at "2026-10-12 14:30" --go

# many videos, spread across one day at random times
python scripts/schedule.py plan examples/batch.example.json --date tomorrow        # preview
python scripts/schedule.py plan examples/batch.example.json --date tomorrow --go   # schedule

python scripts/schedule.py status            # what posted, with links
python scripts/schedule.py cancel <id>       # or: cancel --all
python scripts/schedule.py retry <id>        # a failed or missed post
python scripts/schedule.py pause             # and: resume
```

`add` and `plan` only **preview** until you add `--go`. Times are in your computer's
timezone, or set `TELLA_SCHEDULE_TZ=Africa/Lagos` (any IANA name) in `.env`.

## Safety built in

- **Never posts twice.** Before every publish it checks Tella's own list of what was
  already posted, including posts you made by hand in the app.
- **No bursts.** If the scheduler was down and posts piled up, it spaces them 20
  minutes apart per platform.
- **No 3 am surprises.** A post more than 6 hours late is marked `missed`, not posted.
- **Two tries, then stop.** A post that fails twice stays `failed` until you retry it.
- **Your key stays yours.** It lives in your `.env` and your own Modal secret.

Posting many videos a day is your decision. Platforms flag accounts for bursts and
repeats, which the gap and the checks above are there to avoid, but no tool can
promise how a platform treats your account.

## Alternatives to Modal

The scheduler is one small function (`scripts/runner.py`) that has to be called every
few minutes. Modal is the default because it is free at this size and needs no server.
Anything that can run a Python script on a timer works:

| Scheduler | How |
|---|---|
| **GitHub Actions** | `examples/github-actions.yml`: the queue is a `queue.json` file in a private repo. Free minutes; starts can be 5–30 minutes late. |
| **cron on any server / VPS / Raspberry Pi** | `*/10 * * * * cd /path/to/skill && TELLA_API_KEY=… python scripts/run_once.py queue.json` |
| **Render, Railway, Fly.io, Cloudflare cron jobs** | Run `python scripts/run_once.py queue.json` on a schedule, with the queue file on a persistent disk. |

For these, set `TELLA_SCHEDULE_QUEUE=queue.json` when you run `schedule.py`, so it
writes to the file queue instead of Modal.

## Cost

Modal: a run on an empty queue takes about a second on a small container, every 10
minutes. That is a tiny part of Modal's free monthly credit at the time of writing;
check [modal.com/pricing](https://modal.com/pricing). Tella: whatever plan gives you
API keys and social publishing. Nothing else.

## Status

Early version. The queue logic (due posts, follow-up, no double posts, retries, missed
posts) is tested against simulated Tella responses, and the Modal setup is the one the
author runs. The GitHub Actions example is untested. Do the private test post in
"Set up" before you rely on it, and please open an issue if something breaks.

## Files

```
SKILL.md                    instructions for the agent
SETUP_GUIDE.md              full setup: Modal account, deploy, test, every alternative scheduler
scripts/schedule.py         the CLI (add, plan, status, cancel, retry, pause, resume)
scripts/runner.py           one pass over the queue
scripts/modal_app.py        Modal cron that calls the runner
scripts/run_once.py         the same runner for GitHub Actions / cron (file queue)
scripts/stores.py           Modal Dict or JSON file queue
scripts/tella_api.py        the three Tella API calls it needs
scripts/deploy_modal.sh     deploy / stop on Modal
examples/                   a batch file and a GitHub Actions workflow
```

## License

MIT. Not affiliated with Tella or Modal.
