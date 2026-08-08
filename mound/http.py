"""Shared HTTP session used by all Mound API clients.

Centralizing the session lets every module benefit from the same retry
policy, headers and timeout defaults without duplicating boilerplate.
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from mound import config

_session: requests.Session | None = None


def get_session() -> requests.Session:
    """Return a shared, retry-configured requests session (created lazily)."""
    global _session
    if _session is None:
        session = requests.Session()
        session.headers.update(config.DEFAULT_HEADERS)
        retry = Retry(
            total=config.RETRY_TOTAL,
            backoff_factor=config.RETRY_BACKOFF_FACTOR,
            status_forcelist=config.RETRY_STATUS_FORCELIST,
            allowed_methods=("GET",),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        _session = session
    return _session


def get_json(url: str, params: dict | None = None) -> dict:
    """GET a URL and return the parsed JSON body, raising on HTTP errors."""
    response = get_session().get(url, params=params, timeout=config.REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()
