"""Minimal Tella REST client. Key: TELLA_API_KEY from the environment or a .env file
in the skill folder (Tella -> Settings -> API Keys). The key is never printed.
API reference: https://www.tella.com/docs
"""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.tella.com/v1"
DESTINATIONS = ("youtube", "youtube_shorts", "linkedin", "x", "instagram_post", "instagram_reel", "instagram_story",
                "facebook_post", "facebook_story")  # all the Tella API can publish to (Instagram/Facebook: one Facebook connection)
PRIVACY = {"youtube": ("public", "unlisted", "private"), "youtube_shorts": ("public", "unlisted", "private"),
           "linkedin": ("public", "private"), "facebook_post": ("public", "unlisted", "private")}  # the rest: public only


def _load_env():
    """Read KEY=value lines from the skill's .env without overriding the real environment."""
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


_load_env()


def api_key():
    key = os.environ.get("TELLA_API_KEY")
    if not key:
        raise SystemExit("TELLA_API_KEY is not set. Create one in Tella -> Settings -> API Keys and put it in .env")
    return key


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Tella {e.code}: {e.read().decode()[:300]}") from None


def accounts():
    return call("GET", "/social-accounts")["accounts"]


def publications(video_id):
    """Latest publish of this video per destination, including ones made in the Tella app."""
    return call("GET", f"/videos/{video_id}/publish")["publications"]


def publish(item):
    """Start a publish. Tella renders (or reuses) the export, then uploads. Returns at once."""
    body = {"destination": item["destination"], "title": item["title"]}
    if item.get("description"):
        body["description"] = item["description"]
    if item.get("accountId"):
        body["accountId"] = item["accountId"]
    if item.get("subtitles"):
        body["export"] = {"subtitles": True}
    if item["destination"] in PRIVACY:  # X, Instagram and Facebook stories are always public
        body["privacy"] = item.get("privacy", "public")
    return call("POST", f"/videos/{item['videoId']}/publish", body)["publication"]
