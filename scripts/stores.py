"""Where the queue lives. Both stores behave like a dict of item id -> item."""
import json
import os
from pathlib import Path

NAME = "tella-schedule"


class FileStore(dict):
    """A JSON file. Use with run_once.py (GitHub Actions, cron...)."""

    def __init__(self, path="queue.json"):
        self.path = Path(path)
        super().__init__(json.loads(self.path.read_text()) if self.path.exists() else {})

    def __setitem__(self, k, v):
        super().__setitem__(k, v)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self, indent=1, ensure_ascii=False))
        tmp.replace(self.path)


def open_store():
    """Modal by default; a file when TELLA_SCHEDULE_QUEUE=path/to/queue.json is set."""
    path = os.environ.get("TELLA_SCHEDULE_QUEUE")
    if path:
        return FileStore(path)
    import modal
    try:
        modal.Function.from_name(NAME, "tick").hydrate()
    except Exception:
        raise SystemExit("The Modal scheduler is not deployed, so nothing would ever post. "
                         "Run scripts/deploy_modal.sh first. Nothing was scheduled.")
    return modal.Dict.from_name(NAME, create_if_missing=True)
