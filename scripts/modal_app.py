"""The scheduler on Modal: a cron that calls runner.run() every 10 minutes.

Queue  = Modal Dict   "tella-schedule"
Key    = Modal Secret "tella-schedule" (TELLA_API_KEY)
Deploy = scripts/deploy_modal.sh
A run on an empty queue takes about a second on a tiny container, which fits inside
Modal's free monthly credit (check modal.com/pricing for the current allowance).
"""
import modal

import runner

app = modal.App("tella-schedule")
store = modal.Dict.from_name("tella-schedule", create_if_missing=True)
image = modal.Image.debian_slim(python_version="3.11").add_local_python_source("runner", "tella_api")


@app.function(image=image, schedule=modal.Period(minutes=10), secrets=[modal.Secret.from_name("tella-schedule")],
              timeout=240, max_containers=1)
def tick():
    for line in runner.run(store):
        print(line)
    try:  # Modal drops Dict entries untouched for 7 days: keep waiting posts alive (every 12 h)
        for line in runner.refresh(store):
            print(line)
    except Exception as e:  # never stop posting over this
        print("refresh error:", str(e)[:200])
