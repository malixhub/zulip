#!/usr/bin/env python3
"""Set recognizable sample face avatars for ASDPolicy's four existing demo bots.

Uses the official Zulip REST API. Changes no user other than these demo bots.
"""
import base64
import getpass
import json
import sys
import urllib.error
import urllib.request
import uuid

BASE = "https://chat.asdpolicy.org"
PORTRAITS = {
    "Research Reviewer (Demo)": "https://randomuser.me/api/portraits/men/32.jpg",
    "Policy Analyst (Demo)": "https://randomuser.me/api/portraits/women/44.jpg",
    "Data Specialist (Demo)": "https://randomuser.me/api/portraits/men/75.jpg",
    "Editorial Lead (Demo)": "https://randomuser.me/api/portraits/women/68.jpg",
}

def api(path, email, key, payload=None, content_type=None):
    auth = base64.b64encode(f"{email}:{key}".encode()).decode()
    headers = {"Authorization": "Basic " + auth, "User-Agent": "ASDPolicy-Demo-Avatars/1.0"}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(BASE + "/api/v1/" + path, data=payload, headers=headers,
                                 method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    if result.get("result") != "success":
        raise RuntimeError(str(result))
    return result

def main():
    print("Updates four existing '(Demo)' bot avatars with sample portrait photographs.")
    print("The faces are examples, not pictures of actual ASDPolicy staff.")
    if input("Type FACES to proceed: ").strip() != "FACES":
        return
    email = input("Your Zulip login email: ").strip()
    key = getpass.getpass("Your Zulip API key (hidden): ")
    bots = {bot["full_name"]: bot for bot in api("bots", email, key)["bots"]}
    for name, url in PORTRAITS.items():
        if name not in bots:
            print("Skipping unavailable bot:", name)
            continue
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=25) as response:
            picture = response.read(2_000_000)
        if not picture.startswith(b"\xff\xd8"):
            raise RuntimeError("Expected a JPEG photo from " + url)
        boundary = "----asdpolicy-" + uuid.uuid4().hex
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"demo-photo.jpg\"\r\n"
                f"Content-Type: image/jpeg\r\n\r\n").encode() + picture + f"\r\n--{boundary}--\r\n".encode()
        bot = bots[name]
        result = api("users/me/avatar", bot.get("username") or bot["email"], bot["api_key"],
                     payload=body, content_type="multipart/form-data; boundary=" + boundary)
        print("Updated:", name, result.get("avatar_url", ""))
    print("Done. Reload the chat to see the portraits.")

if __name__ == "__main__":
    try:
        main()
    except (urllib.error.URLError, ValueError, KeyError, RuntimeError) as error:
        print("Stopped:", error, file=sys.stderr)
        sys.exit(1)
