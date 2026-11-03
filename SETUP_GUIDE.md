# Tella Schedule: the full setup guide

Step by step, from nothing to scheduled Tella posts: the Modal account, the Tella key,
deploying the scheduler, a test post, daily use, and the other schedulers you can use
instead of Modal (GitHub Actions, cron, launchd, Windows Task Scheduler, a server).

By Nirvana x Jude · https://www.youtube.com/@nirvanaxjude
Skill: https://github.com/judeolaboboye/modal-scheduler-tella-skill

You can follow this yourself in a terminal, or paste it into an AI agent that can run
commands (Claude Code, Codex CLI, Antigravity / Gemini CLI, Cursor) and say *"set this
up with me"*. The agent does the commands; you do the parts marked **(you)**: creating
accounts, signing in, copying your key, and running the deploy script.

---

## 0. What you are building

Tella can publish a video to YouTube, YouTube Shorts, LinkedIn, X, Instagram and Facebook.
Its API can hold a post for later, but at most 30 days ahead, and it posts exactly what
the video looked like when you scheduled it. This skill keeps your own queue with no
limit on how far ahead, and it checks for double posts. It works like this:

```
your agent / you ──► schedule.py ──► the queue (a list of posts with times)
                                          │
              a cron, every 10 min ───────┘──► runner.py ──► Tella API ──► YouTube / Shorts / LinkedIn / X / IG / FB
```

- **The queue** holds each post: which video, where to, title, text, when.
- **The cron** is anything that runs `runner.py` every few minutes. It posts what is due
  and follows up until Tella returns the post link.

The only choice you make is **where the queue and the cron live**:

| Option | Your computer can be off? | Cost | Setup | Timing | Best for |
|---|---|---|---|---|---|
| **A. Modal** (default) | Yes | Free credit covers it | 5 min | Within ~10 min | Almost everyone |
| **B. GitHub Actions** | Yes | Free (see minutes note) | 15 min | Often 5–30 min late | People who already live in GitHub |
| **C. cron / launchd on your Mac or Linux PC** | **No**, must be on and awake | Free | 5 min | Within ~10 min | Testing, or a computer that is always on |
| **D. Windows Task Scheduler** | **No** | Free | 5 min | Within ~10 min | Windows users with an always-on PC |
| **E. A server / VPS / Raspberry Pi with cron** | Yes (the server stays on) | Server cost | 15 min | Within ~10 min | People who already have a server |

If you are not sure, pick **A. Modal**.

**Not covered by any option:** TikTok (Tella posts it only from inside its app, because
TikTok needs its consent form on every post), Threads and Substack (Tella doesn't post
there). For those, a **free Buffer account** is enough: you upload the Tella video to Buffer
and schedule it there. Section 12 has the steps.

**Instagram and Facebook are covered**: Instagram post, reel and story; Facebook post and story.
Instagram and Facebook come through **one Facebook connection** in Tella (Settings → Connections). Instagram has to be a professional (Business or Creator) account linked to a Facebook Page, which is Meta's rule for outside publishing.

---

## 1. Things you need first (all options)

1. **A Tella account with API access** and your social accounts connected:
   Tella → **Settings → Connections** → connect YouTube, LinkedIn, X and/or Facebook
   (the Facebook connection also brings in Instagram). **(you)** For Instagram: in the
   Instagram app, switch to a professional account (Settings → Account type and tools)
   and link it to a Facebook Page. Then choose the default Page and Instagram account in
   Tella's Connections.
2. **A Tella API key:** Tella → **Settings → API Keys → Create key**. Copy it; you
   paste it in step 3. **(you)** Treat it like a password. Never paste it into a chat,
   a screenshot, a commit or a public file.
3. **Python 3.9 or newer.** Check in a terminal:
   ```bash
   python3 --version        # Windows: py --version
   ```
   If it is missing: Mac `brew install python` (or python.org), Windows python.org
   (tick "Add to PATH"), Linux `sudo apt install python3 python3-pip`.
4. **git:** `git --version`. Mac: it offers to install the developer tools the first
   time. Windows: git-scm.com.
5. **Finished videos in Tella.** The skill only posts. It doesn't cut, edit or caption.

---

## 2. Get the skill

```bash
# Claude Code (installs it as a skill the agent finds by itself)
git clone https://github.com/judeolaboboye/modal-scheduler-tella-skill ~/.claude/skills/tella-schedule
cd ~/.claude/skills/tella-schedule

# Any other agent, or by hand: clone it anywhere
git clone https://github.com/judeolaboboye/modal-scheduler-tella-skill
cd modal-scheduler-tella-skill
```

Every command below runs **from inside this folder**.

## 3. Add your Tella key

```bash
cp .env.example .env
```

Open `.env` in any text editor and paste your key after `TELLA_API_KEY=`, with no spaces
and no quotes. **(you)** Also set your timezone, so the times you type mean your local time:

```
TELLA_API_KEY=tella_pk_xxxxxxxxxxxxxxxx
TELLA_SCHEDULE_TZ=Africa/Lagos
```

(Any IANA name works: `Europe/London`, `America/New_York`, `Asia/Kolkata`...)

`.env` is already in `.gitignore`, so git never uploads it.

## 4. Check the key works

```bash
python3 scripts/schedule.py accounts
```

You should see each connected account (YouTube, LinkedIn, X, Facebook/Instagram) with its ID. If an account
says **RECONNECT IN TELLA**, reconnect it in Tella → Settings → Connections before going
on. If it says the key is missing or gives a `401` error, the key in `.env` is wrong or was
deleted in Tella.

Now pick your scheduler: **section 5 (Modal)**, or one of the alternatives in **section 8**.

---

## 5. Option A: Modal (recommended)

[Modal](https://modal.com) runs small Python functions in the cloud on a timer. The
scheduler is one function that wakes every 10 minutes, takes about a second when nothing
is due, and goes back to sleep. That fits inside Modal's free monthly credit. At the
time of writing the free Starter plan includes $30 of compute a month; check
[modal.com/pricing](https://modal.com/pricing) for today's numbers.

### 5.1 Create your Modal account **(you)**

1. Go to **https://modal.com** and click **Sign up**.
2. Sign up with **GitHub** or **Google**, or with an email address.
3. Modal creates a **workspace** for you, usually named after your username. Everything you
   deploy lives there.
4. Choose the free **Starter** plan if it asks. You don't need a card to start. If
   Modal asks for one, it's for usage above the free credit, and this scheduler
   stays far below it.
5. Keep the dashboard open: **https://modal.com/apps**. Your scheduler shows up here
   after step 5.4.

### 5.2 Install the Modal command line tool

```bash
python3 -m pip install --upgrade modal
python3 -m modal --version
```

If `pip` complains about an "externally managed environment" (newer Mac/Linux Python),
use a virtual environment inside the skill folder:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install modal
```

(With a venv, run `source .venv/bin/activate` in each new terminal before the commands
below. `.venv/` is already ignored by git.)

### 5.3 Connect your computer to your Modal account **(you)**

```bash
python3 -m modal setup
```

This opens your browser. Sign in to Modal and approve the connection. The terminal then says
it stored a token (in `~/.modal.toml`). You do this **once per computer**.

- No browser on this machine (a server)? Run `python3 -m modal token new`, open the link
  it prints on any device, and approve it there.
- Several Modal workspaces? `python3 -m modal profile list` / `modal profile activate <name>`.

Check: `python3 -m modal app list` should run without errors. It's an empty list for now.

### 5.4 Deploy the scheduler **(you run this)**

```bash
scripts/deploy_modal.sh
```

It does three things:
1. Reads `TELLA_API_KEY` from `.env` and saves it as a **Modal secret** named
   `tella-schedule`. The key is stored encrypted in your Modal workspace and never printed.
2. Deploys `scripts/modal_app.py` as the app **tella-schedule** with a function
   `tick` that runs **every 10 minutes**.
3. Creates the queue: a Modal Dict, also named `tella-schedule`.

Expected ending: `Scheduler is ON. It checks the queue every 10 minutes on Modal.`

Agents: let the user run this themselves. It puts their key in their cloud account
and starts a job under their name.

Windows: run it from **Git Bash** or **WSL**, or do the two steps by hand:
```bash
cd scripts
python -m modal secret create tella-schedule TELLA_API_KEY=<your key> --force
python -m modal deploy modal_app.py
```

### 5.5 Check it is running

- Dashboard: **modal.com/apps → tella-schedule → tick**. You see a schedule
  ("every 10 minutes") and, after the first run, a list of runs with their logs.
- Terminal:
  ```bash
  python3 scripts/schedule.py status          # "(nothing)" on an empty queue
  python3 -m modal app list                    # tella-schedule ... deployed
  python3 -m modal app logs tella-schedule     # live log; Ctrl+C to leave
  ```

### 5.6 Test with one private post (do not skip this)

Pick any finished video in Tella. Its ID is in the video's URL or from your agent's
Tella connection (`vid_...`). Then:

```bash
python3 scripts/schedule.py add --video vid_xxx --to youtube --title "Scheduler test" \
  --privacy private --random 00:00-23:59                # preview: shows the time it picked
python3 scripts/schedule.py add --video vid_xxx --to youtube --title "Scheduler test" \
  --privacy private --random 00:00-23:59 --go           # actually queue it
```

The picked time is at least 15 minutes from now. About 10–20 minutes after that time:

```bash
python3 scripts/schedule.py status
```

The test should move `scheduled → sent → posted`, and the last column shows the YouTube
link. Open it: it's a **private** video only you can see. Delete it on YouTube after.
If it says `failed`, read the error (section 10).

### 5.7 Change how often it checks (optional)

In `scripts/modal_app.py`, `schedule=modal.Period(minutes=10)` can become
`modal.Period(minutes=5)` (posts land closer to their time, roughly twice the tiny cost)
or `modal.Cron("*/15 * * * *")` (cron syntax, UTC). Run `scripts/deploy_modal.sh` again
after any change.

### 5.8 Stop, pause, remove

| What | Command |
|---|---|
| Pause posting, keep the queue | `python3 scripts/schedule.py pause` / `resume` |
| Stop the cron completely | `scripts/deploy_modal.sh off` |
| Turn it back on | `scripts/deploy_modal.sh` |
| New Tella key | update `.env`, run `scripts/deploy_modal.sh` again |
| Delete everything on Modal | dashboard → Apps → tella-schedule → Stop; Secrets → delete `tella-schedule`; Storage → Dicts → delete `tella-schedule` |

---

## 6. Using it every day

Ask your agent in plain words:

- "Schedule this Tella video to YouTube Shorts and X tomorrow at 2:30 pm."
- "Post these 7 clips today at random times, at least 45 minutes apart."
- "What went out today?" / "Cancel the LinkedIn one." / "Pause the scheduler."

Or run it yourself:

```bash
# one video at an exact time (your TELLA_SCHEDULE_TZ)
python3 scripts/schedule.py add --video vid_xxx --to youtube_shorts,x \
  --title "Title" --description "Post text" --at "2026-11-12 14:30" --go

# one video at a random time inside a window
python3 scripts/schedule.py add --video vid_xxx --to linkedin --title "..." \
  --random 08:00-21:30 --date tomorrow --go

# many videos across one day (copy examples/batch.example.json and fill it in)
python3 scripts/schedule.py plan my-batch.json --date tomorrow --window 08:00-21:30 --gap 45        # preview
python3 scripts/schedule.py plan my-batch.json --date tomorrow --window 08:00-21:30 --gap 45 --go   # schedule
```

`add` and `plan` only **preview** until you add `--go`. With `plan`, the times are drawn
again on `--go`, so they differ from the preview. That's on purpose.

Batch file fields, per video: `videoId`, `title`, `description`, `destinations`
(`youtube`, `youtube_shorts`, `linkedin`, `x`, `instagram_post`, `instagram_reel`,
`instagram_story`, `facebook_post`, `facebook_story`), and optional `privacy`
(`public|unlisted|private` for YouTube and Facebook posts, `public|private` for LinkedIn;
X, Instagram and Facebook stories are always public), `subtitles` (true = burn Tella's
subtitles in), and per-destination text such as `"x": {"description": "shorter text"}`.

| Need | Command |
|---|---|
| What is scheduled / posted / failed, with links | `schedule.py status` |
| Cancel one / everything | `schedule.py cancel <id>` / `cancel --all` |
| Retry a failed or missed post | `schedule.py retry <id>` |
| Pause / resume all posting | `schedule.py pause` / `resume` |

Platform limits Tella enforces: Shorts must be vertical or square and at most 3 min;
LinkedIn at most 30 min; X at most 20 min (longer with Premium); Instagram post/reel at
most 15 min and 300 MB, Instagram story at most 60 s and 100 MB; Facebook story vertical
and at most 60 s; no 4K export for Instagram; stories show no text.

---

## 7. Safety built in (all options)

- **Never posts twice.** Before every publish it checks Tella's own list of posts for
  that video, including ones you made by hand in the Tella app.
- **No bursts.** If posts piled up while the scheduler was down, it spaces them 20
  minutes apart per platform.
- **No 3 am surprises.** A post more than 6 hours late is marked `missed`, not posted.
- **Two tries, then stop.** A post that fails twice stays `failed` until you retry it.
- **Your key stays yours:** only in your `.env` and your own scheduler's secret store.

---

## 8. Alternatives to Modal

All of them run the same file, `scripts/run_once.py`, which does one pass over a
**JSON file queue** (`queue.json`) instead of the Modal Dict. Two settings change:

1. Add this to `.env`, so `schedule.py` writes to the file instead of Modal:
   ```
   TELLA_SCHEDULE_QUEUE=queue.json
   ```
2. Your scheduler runs, every 5–15 minutes, from the skill folder:
   ```bash
   python3 scripts/run_once.py queue.json
   ```
   `run_once.py` reads `TELLA_API_KEY` from `.env` itself, so the key never has to go
   in a crontab line or a log.

Test any option with a manual run first, then the private test post from 5.6:

```bash
python3 scripts/run_once.py queue.json     # prints nothing when nothing is due
```

**Important:** the queue file must be the same file for both sides. `schedule.py`
writes it, and the scheduler reads and updates it. On your own computer or server that's
automatic. On GitHub Actions the file travels through git (8B).

### 8B. GitHub Actions

GitHub runs the workflow on its machines on a timer, so your computer can be off.
**The workflow is an untested example.** Do the private test post first.

**Minutes:** a private repo on GitHub Free gets 2,000 Action minutes a month, and each run
counts as at least 1 minute. Every 15 minutes = ~2,900 minutes a month, **over the free
amount**. Every 30 minutes = ~1,450, which fits. A public repo has unlimited minutes, but
then your queue (video IDs, titles, post text, times) is public. Your key stays
secret either way.

**Steps**

1. **(you)** On github.com: **New repository** → name it e.g. `my-tella-schedule` →
   **Private** → Create.
2. Copy the skill into it and remove `queue.json` from `.gitignore` (the queue has to
   be committed so GitHub can read it):
   ```bash
   git clone https://github.com/<you>/my-tella-schedule && cd my-tella-schedule
   cp -R /path/to/modal-scheduler-tella-skill/{scripts,examples,.env.example,.gitignore} .
   sed -i.bak '/^queue.json$/d' .gitignore && rm .gitignore.bak
   echo '{}' > queue.json
   mkdir -p .github/workflows
   cp examples/github-actions.yml .github/workflows/tella-schedule.yml
   ```
3. Set the timer to every 30 minutes on a private repo. In
   `.github/workflows/tella-schedule.yml`, change `"*/15 * * * *"` to
   `"*/30 * * * *"`. Also add a pull before the save, so it never clashes with your own
   pushes. The **Save results** step becomes:
   ```yaml
         - name: Save results
           run: |
             git config user.name "tella-schedule"
             git config user.email "actions@users.noreply.github.com"
             git add queue.json
             git diff --cached --quiet || (git commit -m "queue update" && git pull --rebase && git push)
   ```
4. **(you)** Add your key as a secret: repo → **Settings → Secrets and variables →
   Actions → New repository secret** → name `TELLA_API_KEY`, value your key.
5. Locally: `cp .env.example .env`, put your key in it, and add
   `TELLA_SCHEDULE_QUEUE=queue.json` and your `TELLA_SCHEDULE_TZ`.
6. Push:
   ```bash
   git add . && git commit -m "tella schedule" && git push
   ```
7. Test the workflow: repo → **Actions → tella-schedule → Run workflow**. It should go
   green in under a minute.

**Every time you schedule:**
```bash
git pull                                              # get the latest results first
python3 scripts/schedule.py plan batch.json --go      # writes queue.json
git add queue.json && git commit -m "schedule" && git push
```
And `git pull` before `schedule.py status`, because the workflow commits the results back.

Know this: GitHub often starts scheduled runs 5–30 minutes late, and at busy times
can skip one. Treat times as "around". GitHub can also turn off scheduled
workflows in a repo with no activity for a long time (60 days on public repos). If
posts stop, check the **Actions** tab and re-enable it.

**GitLab instead of GitHub:** the same idea works with a GitLab **scheduled pipeline**
(CI/CD → Schedules) running `python3 scripts/run_once.py queue.json` and committing
`queue.json` back with a project access token.

### 8C. cron on your Mac or Linux computer

Works only while the computer is **on and awake**. A Mac that sleeps at night posts
late or marks posts `missed` (more than 6 hours late). Good for testing, or for an
always-on machine.

1. Find the full paths (cron knows nothing about your terminal setup):
   ```bash
   pwd                 # e.g. /Users/you/modal-scheduler-tella-skill
   which python3       # e.g. /opt/homebrew/bin/python3  (or your .venv/bin/python)
   ```
2. `crontab -e` and add one line (every 10 minutes, log to a file):
   ```
   */10 * * * * cd /Users/you/modal-scheduler-tella-skill && /opt/homebrew/bin/python3 scripts/run_once.py queue.json >> cron.log 2>&1
   ```
3. Save and exit (in vim: `Esc`, then `:wq`). Check with `crontab -l`. Remove later with
   `crontab -e` (delete the line).
4. **Mac only:** if `cron.log` says *Operation not permitted*, the folder is in a
   protected place (Desktop, Documents, Downloads). Move the skill to your home folder,
   or give cron Full Disk Access (System Settings → Privacy & Security → Full Disk
   Access → `+` → press Cmd+Shift+G → `/usr/sbin/cron`). Or use launchd (8D).

Popular cron timings, if you want another rhythm (cron uses the computer's timezone):

| Expression | Meaning |
|---|---|
| `*/5 * * * *` | every 5 minutes (closest to the exact time) |
| `*/10 * * * *` | every 10 minutes (the default rhythm) |
| `*/15 * * * *` | every 15 minutes |
| `*/10 7-22 * * *` | every 10 minutes, only 07:00–22:59 |
| `*/10 * * * 1-5` | every 10 minutes, Monday to Friday only |

### 8D. launchd on a Mac (the Mac's own scheduler)

launchd is Apple's replacement for cron. If the Mac was asleep, it runs the job once
when the Mac wakes up.

1. Create `~/Library/LaunchAgents/com.you.tella-schedule.plist` (change the two paths):
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
     <key>Label</key><string>com.you.tella-schedule</string>
     <key>WorkingDirectory</key><string>/Users/you/modal-scheduler-tella-skill</string>
     <key>ProgramArguments</key>
     <array>
       <string>/opt/homebrew/bin/python3</string>
       <string>scripts/run_once.py</string>
       <string>queue.json</string>
     </array>
     <key>StartInterval</key><integer>600</integer>
     <key>StandardOutPath</key><string>/Users/you/modal-scheduler-tella-skill/launchd.log</string>
     <key>StandardErrorPath</key><string>/Users/you/modal-scheduler-tella-skill/launchd.log</string>
   </dict>
   </plist>
   ```
   (`600` seconds = every 10 minutes.)
2. Turn it on and check it:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.you.tella-schedule.plist
   launchctl list | grep tella-schedule
   ```
3. Turn it off: `launchctl unload ~/Library/LaunchAgents/com.you.tella-schedule.plist`.

To keep the Mac awake while plugged in: System Settings → Battery (or Energy) → Options
→ "Prevent automatic sleeping when the display is off".

### 8E. Windows Task Scheduler

Works only while the PC is **on**.

1. Find the paths: the skill folder (e.g. `C:\Users\you\modal-scheduler-tella-skill`)
   and Python (`py` usually works; or `where python`).
2. In **Command Prompt**, one line (every 10 minutes):
   ```bat
   schtasks /create /tn "tella-schedule" /sc minute /mo 10 /tr "cmd /c cd /d C:\Users\you\modal-scheduler-tella-skill && py scripts\run_once.py queue.json >> cron.log 2>&1"
   ```
3. Check: open **Task Scheduler** → Task Scheduler Library → `tella-schedule` → History.
   Run it now: `schtasks /run /tn "tella-schedule"`. Remove: `schtasks /delete /tn "tella-schedule" /f`.
4. In the task's properties you can tick **Run whether user is logged on or not** and,
   under Conditions, **Wake the computer to run this task**.

### 8F. A server, VPS or Raspberry Pi

Any always-on Linux machine (a $4–6 VPS, a Raspberry Pi at home, a spare PC) works like
8C, and your laptop can be off.

1. On the server: install Python 3 and git, clone the skill, `cp .env.example .env`, add
   the key, `TELLA_SCHEDULE_QUEUE=queue.json` and `TELLA_SCHEDULE_TZ`.
2. Add the cron line from 8C with the server's paths (`which python3`).
3. Schedule **on the server**, so both sides use the same `queue.json`:
   ```bash
   ssh you@server 'cd ~/modal-scheduler-tella-skill && python3 scripts/schedule.py plan batch.json --go'
   ```
   (copy the batch file up first: `scp batch.json you@server:~/modal-scheduler-tella-skill/`),
   or tell your agent to run the commands over SSH.

**Managed cloud cron services** (Render cron jobs, Railway, Fly.io, Google Cloud
Scheduler + Cloud Run, AWS EventBridge + Lambda) can run `run_once.py` too, but their
disks usually reset between runs. The queue then has to live in git (the same way as 8B)
or you have to add a database. For most people, Modal (A) or GitHub Actions (B) is
less work.

---

## 9. Moving between options

The Modal queue and the file queue are separate. To switch:

1. `python3 scripts/schedule.py status`: let what is due post, or `cancel --all`.
2. Switching to Modal: remove `TELLA_SCHEDULE_QUEUE` from `.env`, run section 5.
   Switching away from Modal: `scripts/deploy_modal.sh off`, add `TELLA_SCHEDULE_QUEUE=queue.json`.
3. Schedule the remaining posts again on the new one.

Never run both on the same posts. The double-post check protects you, but don't rely on it.

---

## 10. Troubleshooting

| You see | What it means / fix |
|---|---|
| `TELLA_API_KEY is not set` | `.env` missing, or the key line is empty. Step 3. |
| `Tella 401` | Key wrong or deleted. New key in Tella, update `.env`, and on Modal run `deploy_modal.sh` again. |
| `Tella 403` / "not connected" | Reconnect that social account in Tella → Settings → Connections, then `schedule.py retry <id>`. |
| `The Modal scheduler is not deployed` | You haven't run `scripts/deploy_modal.sh` yet, or it was stopped. Nothing was queued. |
| `modal: command not found` | Use `python3 -m modal ...`, or activate the venv (5.2). |
| `modal setup` opens no browser | `python3 -m modal token new` and open the printed link. |
| Posts stay `scheduled` past their time | The cron isn't running. Modal: dashboard → tella-schedule → tick → runs. Cron: `cron.log`. GitHub: Actions tab. Also check `schedule.py status` doesn't say paused. |
| Post shows `missed` | It was over 6 hours late (scheduler or computer was off). `schedule.py retry <id>` posts it now. |
| Post shows `failed` | Read the error in `status`. Shorts over 3 min or horizontal, an X video over 20 min, or a disconnected account are the usual causes. Fix, then `retry`. |
| `sent` for a long time | Tella is still rendering and uploading a long video. It becomes `posted` with a link. |
| GitHub run is red | Click it for the log. Usually a missing `TELLA_API_KEY` secret or a push conflict (step 3 in 8B). |
| "N posts to … don't fit on …" | Too many posts for the window and gap: pick tomorrow, a smaller `--gap`, or fewer posts. |

## 11. Costs at a glance

| Option | Cost for this job |
|---|---|
| Modal | Inside the free monthly credit (about a second of compute every 10 minutes) |
| GitHub Actions | Free: public repo unlimited; private repo every 30 min fits the 2,000 free minutes |
| cron / launchd / Task Scheduler | Free; your computer has to stay on |
| VPS / Raspberry Pi | What the machine costs you |
| Tella | Your plan with API keys and social publishing |
| Buffer (TikTok, Threads, Substack) | Free plan: 3 channels, exactly these three |

Prices and free limits change. Check modal.com/pricing and GitHub's Actions billing
page before relying on the numbers here.

---

## 12. TikTok, Threads and Substack: a free Buffer account

Tella's API can't post to these three, so neither this skill nor any cron can. A free
[Buffer](https://buffer.com) account can. Buffer connects to TikTok, Threads and Substack
and posts your video at the time you choose. Use the same video you finished in Tella.
The free plan allows **3 channels**, which fits exactly TikTok, Threads and Substack. Post to
Instagram and Facebook through Tella (this skill), so they don't use up a Buffer channel.

### 12.1 Create the account and connect the channels **(you)**

1. Go to **https://buffer.com** → **Get started**. Sign up with email or Google, and
   choose the **Free** plan.
2. **Channels → Connect a channel**, then for each one:
   - **TikTok:** sign in to TikTok in the window Buffer opens and approve Buffer.
   - **Threads:** sign in with the Instagram account your Threads profile belongs to and approve it.
   - **Substack:** sign in to Substack and pick your publication. Buffer posts to it as Substack Notes.
3. The channels show in Buffer's left sidebar. A channel marked "reconnect" needs
   step 2 again.

### 12.2 Get the video out of Tella

1. Open the finished video in Tella → **Download** (or Share → Download) → MP4. For
   TikTok and Threads use a vertical (9:16) video.
2. Want captions burned in? Turn subtitles on in the export first.

### 12.3 Schedule it in Buffer **(you, or your agent with you)**

1. **Create post** → tick the channels (TikTok, Threads, Substack…).
2. **Upload** the MP4 from Tella and paste the caption. Buffer lets you change the text
   per channel, so TikTok can keep hashtags and Substack can read like a note.
3. **Schedule** → pick the date and time (Buffer uses the timezone in its settings; set
   yours under Settings → General) → **Schedule post**.
4. Check **Queue**: the post sits there until its time, then Buffer posts it and shows it under **Sent**.

Use the same times as the rest of your plan (from `schedule.py status`), so each clip
goes out everywhere around the same time.

### 12.4 Having your agent do it

Buffer has an API, but it takes a **public link** to the video file, not an upload from
your computer. The usual way: export the video in Tella, use that export's download
link as the video link in Buffer, and **don't schedule further ahead than that link
stays valid**. Without an API key, the agent prepares the captions and times and you
upload in Buffer, which takes a minute per post.

TikTok has a second option: schedule it right inside Tella (clip → **Share → Publish → TikTok →
"At a time I pick"**, up to 30 days ahead). Then you don't need Buffer for TikTok.

---

MIT. Not affiliated with Tella, Modal, GitHub or Buffer.
