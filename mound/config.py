"""Shared constants: API base URLs, headers and defaults."""

from __future__ import annotations

STATSAPI_BASE = "https://statsapi.mlb.com/api"
STATSAPI_V1 = f"{STATSAPI_BASE}/v1"

SAVANT_BASE = "https://baseballsavant.mlb.com"
SAVANT_GAMEFEED_URL = f"{SAVANT_BASE}/gf"

# MLB's Stats API groups all affiliated leagues under sportId=1 for MLB itself.
MLB_SPORT_ID = 1

DEFAULT_SEASON_START_MONTH = 3  # spring training/season generally begins in March

USER_AGENT = "mound/0.1 (+https://github.com/stiles/mound; personal project)"

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Referer": "https://www.mlb.com/",
}

# Reasonable network defaults for a courteous client against unofficial endpoints.
REQUEST_TIMEOUT = 15
RETRY_TOTAL = 4
RETRY_BACKOFF_FACTOR = 1.5
RETRY_STATUS_FORCELIST = (429, 500, 502, 503, 504)
