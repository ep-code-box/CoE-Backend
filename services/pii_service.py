"""PID 기반 개인정보 탐지/마스킹 유틸리티."""
from __future__ import annotations

import os
from typing import List, Tuple
from typing_extensions import TypedDict

import pidpy
from pidpy.pidpython import (
    PID,
    StrPartVector,
    PID_BIT_ALL,
    PID_OPTION_CHECK_DIGIT,
)

ENABLE_PID = os.getenv("ENABLE_PID_DETECTION", "true").lower() in {"1", "true", "yes", "on"}
DATA_PATH = os.getenv("PID_DATA_PATH") or os.path.dirname(pidpy.__file__)
_INITIALIZED = False


class PIIHit(TypedDict):
    value: str
    type: str
    start: int
    end: int


def initialize_pid() -> None:
    """PID 리소스를 선로드."""
    global _INITIALIZED
    if _INITIALIZED or not ENABLE_PID:
        return
    if not PID.Init(DATA_PATH, True, False, False, False):
        raise RuntimeError(f"PID init failed (data_path={DATA_PATH})")
    PID.SetOption(PID_OPTION_CHECK_DIGIT)
    _INITIALIZED = True


def terminate_pid() -> None:
    """PID 리소스 해제."""
    global _INITIALIZED
    if not _INITIALIZED:
        return
    PID.Terminate()
    _INITIALIZED = False


def detect_pii(text: str) -> List[PIIHit]:
    """문자열에서 개인정보 후보를 찾아 리턴."""
    if not ENABLE_PID or not text:
        return []
    parts = StrPartVector()
    PID.RunType(text, parts, PID_BIT_ALL)
    hits: List[PIIHit] = []
    for part in parts:
        start = part.begin_syll
        end = part.begin_syll + part.len_syll
        hits.append(
            {
                "value": text[start:end],
                "type": PID.GetTypeSimpleName(part.type),
                "start": start,
                "end": end,
            }
        )
    return hits


def mask_pii(text: str, hits: List[PIIHit], mask_char: str = "*") -> str:
    """탐지된 구간을 마스킹."""
    if not hits:
        return text
    chars = list(text)
    for hit in hits:
        for idx in range(hit["start"], hit["end"]):
            if 0 <= idx < len(chars):
                chars[idx] = mask_char
    return "".join(chars)


def scrub_text(text: str) -> Tuple[str, List[PIIHit]]:
    """텍스트를 마스킹 후 (마스킹된 문자열, 탐지목록)을 반환."""
    hits = detect_pii(text)
    if not hits:
        return text, []
    return mask_pii(text, hits), hits
