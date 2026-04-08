"""
store.py — read/write workout_data.json to/from GitHub via REST API
"""
import json
import base64
import requests


def _headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def _url(cfg):
    return (
        f"https://api.github.com/repos/"
        f"{cfg['github_username']}/{cfg['github_repo']}/"
        f"contents/{cfg['data_file']}"
    )


def load_data(cfg):
    """
    Returns (data_dict, sha).
    sha is None when the file doesn't exist yet.
    """
    r = requests.get(_url(cfg), headers=_headers(cfg["github_token"]), timeout=10)
    if r.status_code == 404:
        return {}, None
    r.raise_for_status()
    payload = r.json()
    content = base64.b64decode(payload["content"]).decode("utf-8")
    return json.loads(content), payload["sha"]


def save_data(cfg, data, sha=None):
    """
    Upsert workout_data.json.  Returns new sha.
    sha must be provided when updating an existing file.
    """
    encoded = base64.b64encode(json.dumps(data, indent=2).encode()).decode()
    body = {"message": "chore: update workout data", "content": encoded}
    if sha:
        body["sha"] = sha
    r = requests.put(
        _url(cfg),
        headers=_headers(cfg["github_token"]),
        json=body,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["content"]["sha"]
