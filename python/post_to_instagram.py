"""Post a photo to Instagram through postcache.

    POSTCACHE_API_KEY=pc_live_... IG_USER_ID=... IG_ACCESS_TOKEN=... python3 post_to_instagram.py photo.jpg "Caption"

1. Upload the file to postcache; it checks the photo against Instagram's feed rules (convert=pad fixes size and format).
2. Give the public URL to the Instagram Graph API and publish.
3. Delete the file from postcache.
"""
import json
import mimetypes
import os
import sys
import time
import urllib.parse
import urllib.request

POSTCACHE = "https://postcache.dev/v1/media"
GRAPH = "https://graph.facebook.com/v23.0/"


def postcache(method, url, data=None, headers=None):
    req = urllib.request.Request(url, data, {"authorization": f"Bearer {os.environ['POSTCACHE_API_KEY']}", **(headers or {})}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, (json.load(r) if r.status != 204 else None)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def graph(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    body = urllib.parse.urlencode(params).encode()
    url = GRAPH + path + ("" if method == "POST" else "?" + body.decode())
    with urllib.request.urlopen(urllib.request.Request(url, body if method == "POST" else None, method=method)) as r:
        return json.load(r)


def upload(path):
    with open(path, "rb") as f:
        data = f.read()
    status, r = postcache("PUT", POSTCACHE + "?convert=pad", data, {
        "x-target": "instagram.feed",
        "x-filename": os.path.basename(path),
        "content-type": mimetypes.guess_type(path)[0] or "application/octet-stream",
    })
    while status == 202 or r.get("status") == "converting":  # postcache is fixing the file
        time.sleep(3)
        status, r = postcache("GET", f"{POSTCACHE}/{r['id']}")
    if not r.get("url"):
        sys.exit(f"postcache: {json.dumps(r.get('checks') or r)}")
    return r["id"], r["url"]


def main(path, caption):
    media_id, url = upload(path)
    try:
        ig = os.environ["IG_USER_ID"]
        container = graph("POST", f"{ig}/media", image_url=url, caption=caption)["id"]
        for _ in range(30):  # Instagram fetches the URL in the background
            if graph("GET", container, fields="status_code")["status_code"] == "FINISHED":
                break
            time.sleep(5)
        post = graph("POST", f"{ig}/media_publish", creation_id=container)["id"]
        print("published:", graph("GET", post, fields="permalink")["permalink"])
    finally:
        postcache("DELETE", f"{POSTCACHE}/{media_id}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
