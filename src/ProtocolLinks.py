"""Parsing and validation of crosspatch: links (GameBanana 1-Click install).

Two shapes reach the app, from the browser or from a second instance through
the single-instance socket:

    crosspatch:<download url>,<item type>,<item id>[,<archive ext>]
    crosspatch://install?url=<GameBanana page url>

Anything on the machine can open such a link or write to the local socket, so
nothing here is trusted. The download URL used to be taken as is, which let a
crafted link make CrossPatch fetch and extract an archive from any server
while the confirmation dialog showed a genuine GameBanana mod.
"""

import re
from urllib.parse import unquote, urlsplit

ALLOWED_ARCHIVES = {"zip", "7z", "rar"}
_ITEM_TYPE = re.compile(r"^[A-Za-z]{2,20}$")
_ITEM_ID = re.compile(r"^\d{1,12}$")


def is_gamebanana_url(url):
    """True for an https URL on gamebanana.com or one of its subdomains."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    return parts.scheme == "https" and (host == "gamebanana.com" or host.endswith(".gamebanana.com"))


def parse(url):
    """Returns a dict describing the link, or raises ValueError.

    {"kind": "schema", "download_url", "item_type", "item_id", "file_ext", "page_url"}
    {"kind": "page", "page_url"}
    """
    url = (url or "").strip()
    if not url.lower().startswith("crosspatch:"):
        raise ValueError("Not a crosspatch: link.")

    body = url[len("crosspatch:"):]

    if body.startswith("//install?url="):
        page_url = unquote(body[len("//install?url="):])
        if not is_gamebanana_url(page_url):
            raise ValueError("The link does not point to a GameBanana page.")
        return {"kind": "page", "page_url": page_url}

    # Some browsers hand the link over as crosspatch://https://...
    if body.startswith("//") and body[2:].lower().startswith("http"):
        body = body[2:]

    parts = body.split(",")
    if len(parts) < 3:
        raise ValueError("The link is incomplete.")

    download_url, item_type, item_id = (p.strip() for p in parts[:3])
    file_ext = (parts[3].strip().lower().lstrip(".") if len(parts) > 3 else "") or "zip"

    if not is_gamebanana_url(download_url):
        raise ValueError("The download does not come from GameBanana.")
    if not _ITEM_TYPE.match(item_type):
        raise ValueError(f"Unexpected submission type '{item_type}'.")
    if not _ITEM_ID.match(item_id):
        raise ValueError(f"Unexpected submission id '{item_id}'.")
    if file_ext not in ALLOWED_ARCHIVES:
        raise ValueError(f"Unsupported archive type '{file_ext}'.")

    return {
        "kind": "schema",
        "download_url": download_url,
        "item_type": item_type,
        "item_id": item_id,
        "file_ext": file_ext,
        "page_url": f"https://gamebanana.com/{item_type.lower()}s/{item_id}",
    }
