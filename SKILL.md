---
name: tella-schedule
description: Schedule Tella videos to post later to YouTube, YouTube Shorts, LinkedIn, X, Instagram (post, reel, story) and Facebook (post, story) without opening Tella. Tella's own scheduling stops at 30 days ahead, so this queues each post with a time and a free cloud cron (Modal by default; GitHub Actions or any cron as alternatives) publishes it through the Tella API when due. Use when the user says "schedule this Tella video", "post these clips at different times today", "drip my Tella clips", "/tella-schedule", or asks how to schedule Tella posts. Does NOT cover TikTok, Threads or Substack: for those, point the user to a free Buffer account (SETUP_GUIDE.md section 12).
---

# Tella Schedule

Tella can publish a video to YouTube, YouTube Shorts, LinkedIn, X, Instagram and
Facebook. Its own `scheduledAt` reaches at most 30 days ahead and posts the export made
at scheduling time. This skill keeps its own queue (any distance ahead, checked for
double posts, spaced out), and the publish happens at the due time. You put posts in a queue with a time; a small cloud job
checks the queue every 10 minutes and tells Tella to publish whatever is due.

Nothing has to stay open: not Tella, not the user's computer, not this chat.

## What it can and cannot post to

| Platform | Scheduled by this skill? | Why |
|---|---|---|
| YouTube, YouTube Shorts | Yes | Tella API |
| LinkedIn | Yes | Tella API |
| X | Yes | Tella API |
| TikTok | **No** | TikTok requires its consent form on every post, so Tella only posts to TikTok from inside the Tella app |
| Instagram (post, reel, story) | Yes | Tella API: `instagram_post`, `instagram_reel`, `instagram_story` |
| Facebook (post, story) | Yes | Tella API: `facebook_post`, `facebook_story` |
| Threads, Substack | **No** | Tella does not publish to them at all |

Say this to the user up front if they mention any of the "No" platforms. For those,
**For TikTok, Threads and Substack, use a free Buffer account.** Buffer's free plan is enough to connect these channels (it covers a few channels; check buffer.com/pricing for today's number). Export or download the finished video from Tella, upload it to Buffer, add the caption and pick the time. Buffer then posts it. Full steps: `SETUP_GUIDE.md` section 12.

Instagram and Facebook come through **one Facebook connection** in Tella (Settings → Connections). Instagram has to be a professional (Business or Creator) account linked to a Facebook Page, which is Meta's rule for outside publishing.

## Requirements (check before anything else)
1. A Tella account with the accounts connected in **Settings → Connections**, and an
   API key from **Settings → API Keys** saved as `TELLA_API_KEY` in this skill's `.env`.
2. The videos are already in Tella and finished (this skill does not edit).
3. A scheduler the agent can reach from the terminal. Default **Modal**:
   `pip install modal` and `modal setup` done once by the user (free account).
   Alternatives: `examples/github-actions.yml`, or any cron that can run
   `scripts/run_once.py` every 5–15 minutes.
4. Python 3.9+. No other packages.

Never print the API key, never write it anywhere but `.env`.

## First-time setup
The full walk-through for the user (Modal account, deploy, test post, and every
alternative scheduler with exact steps) is `SETUP_GUIDE.md`. Follow it with them.
1. `python scripts/schedule.py accounts` → confirms the key and lists connected accounts.
   Any account marked `RECONNECT IN TELLA` must be fixed by the user in Tella first.
2. Ask the user to run `scripts/deploy_modal.sh` **themselves** (it stores the key as a
   Modal secret and starts a cron on their account, so it is their call, not yours).
3. `python scripts/schedule.py status` → works and shows `(nothing)`.

## Scheduling

Always preview first, show the user the table, and only add `--go` after they say yes.
Posting is public and happens under their name.

**One video**
```bash
python scripts/schedule.py add --video vid_xxx --to youtube_shorts,x \
  --title "Title" --description "Post text" --at "2026-10-12 14:30"        # exact time
python scripts/schedule.py add --video vid_xxx --to linkedin --title "..." \
  --random 08:00-21:30 --date tomorrow                                     # random time in a window
```

**Many videos in one day, at random times** (the usual case for a batch of clips)
1. Write a batch file like `examples/batch.example.json`: one entry per video with
   `videoId`, `title`, `description`, `destinations`, and optional per-destination text
   (`"x": {"description": "..."}`), `privacy`, `subtitles`.
2. `python scripts/schedule.py plan batch.json [--date tomorrow] [--window 08:00-21:30] [--gap 45]`
3. With the user's OK: same command plus `--go`. The times are drawn again, so they
   differ from the preview. That is intended; say so.

If it says the posts don't fit in what is left of the day, ask the user: tomorrow, a
smaller gap, or fewer posts. Don't decide for them.

Video IDs: from the Tella MCP (`list_videos`, `search_videos`) or the video's URL.
Options: `--privacy public|unlisted|private` (default public; YouTube and Facebook posts take all three, LinkedIn public|private, X, Instagram and Facebook stories public only),
`--subtitles` burns Tella's subtitles into the export, `--account <id>` when several
accounts are connected for one destination.

## Following up
| Need | Command |
|---|---|
| What posted, with links | `schedule.py status` |
| Stop a post / everything | `schedule.py cancel <id>` / `cancel --all` |
| Retry a `failed` or `missed` post (once) | `schedule.py retry <id>` |
| Stop / restart the whole scheduler | `schedule.py pause` / `resume` |

Statuses: `scheduled` → `sending` → `sent` (Tella is rendering and uploading) →
`posted` (has the link) or `failed`. `missed` = it was more than 6 hours late (the
scheduler was down), so it was not posted at an odd hour.

## Rules for the agent
- Never add `--go` without the user's explicit yes for that exact plan.
- Never call the Tella publish endpoint yourself to "help" a queued post along; that
  is how double posts happen. The queue checks Tella's own publication list before
  every publish and will not post a video twice to the same destination.
- A post that failed twice stays failed. Read the error to the user. `403` or "not
  connected" means they reconnect the account in Tella.
- Limits Tella enforces: YouTube Shorts must be vertical or square and at most 3
  minutes; LinkedIn at most 30 minutes; X at most 20 minutes (longer with Premium);
  Instagram post/reel at most 15 minutes and 300 MB, Instagram story at most 60 s and
  100 MB, Facebook story vertical and at most 60 s; no 4K export for Instagram. Stories show no text.
- Don't schedule bursts. Keep the default gap unless the user asks otherwise; many
  posts in a few minutes is what gets accounts flagged.

## How it works (for debugging)
- `scripts/schedule.py` — the CLI. Writes items to the queue.
- `scripts/runner.py` — one pass: follow up on uploads, publish what is due.
- `scripts/modal_app.py` — Modal cron (every 10 min) calling the runner. Queue = Modal
  Dict `tella-schedule`, key = Modal secret `tella-schedule`.
- `scripts/run_once.py` + `scripts/stores.py` — the same runner on a JSON file queue
  (`TELLA_SCHEDULE_QUEUE=queue.json`) for GitHub Actions or plain cron.
- `scripts/tella_api.py` — `GET /v1/social-accounts`, `GET|POST /v1/videos/{id}/publish`.
- Times are stored in UTC and shown in `TELLA_SCHEDULE_TZ` (default: local timezone).
  Posts go out within about 10 minutes after their time.
