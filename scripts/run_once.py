#!/usr/bin/env python3
"""One pass of the scheduler against a JSON file queue. For any scheduler that is not
Modal: GitHub Actions, cron on a server, Cloudflare/Render/Railway cron jobs, etc.

  TELLA_API_KEY=... python scripts/run_once.py [queue.json]

Call it every 5 to 15 minutes. See examples/github-actions.yml.
"""
import sys

import runner
from stores import FileStore

if __name__ == "__main__":
    for line in runner.run(FileStore(sys.argv[1] if len(sys.argv) > 1 else "queue.json")):
        print(line)
