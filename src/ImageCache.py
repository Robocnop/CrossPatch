"""Downloads preview images once per session and hands them out as QImage.

Browsing back and forth between pages used to download every thumbnail
again. Raw bytes are kept rather than QImage objects because bytes are cheap
and can be shared between threads without any Qt involvement.

Only QImage is produced here: QPixmap may only be created on the GUI thread,
and the loaders that call this run on worker threads.
"""

import threading
from collections import OrderedDict

import requests
from PySide6.QtGui import QImage

from Constants import BROWSER_USER_AGENT

_MAX_ENTRIES = 300
_cache = OrderedDict()
_lock = threading.Lock()


def _get_bytes(url):
    with _lock:
        data = _cache.get(url)
        if data is not None:
            _cache.move_to_end(url)
        return data


def _put_bytes(url, data):
    with _lock:
        _cache[url] = data
        _cache.move_to_end(url)
        while len(_cache) > _MAX_ENTRIES:
            _cache.popitem(last=False)


def fetch_image(url, timeout=10):
    """Returns the image at url as a QImage. Raises on network or decode errors."""
    data = _get_bytes(url)
    if data is None:
        response = requests.get(url, headers={'User-Agent': BROWSER_USER_AGENT}, timeout=timeout)
        response.raise_for_status()
        data = response.content
        _put_bytes(url, data)

    image = QImage()
    if not image.loadFromData(data):
        with _lock:
            _cache.pop(url, None)
        raise ValueError(f"The image at {url} could not be decoded.")
    return image
