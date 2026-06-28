from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
SUPPORTED = {"nb", "en", "de", "fr"}


@lru_cache(maxsize=16)
def load_translation(lang: str) -> dict:
    lang = lang if lang in SUPPORTED else "nb"
    path = ROOT / "translations" / f"{lang}.json"
    return json.loads(path.read_text(encoding="utf-8"))
