"""Persist Kayakalp admin switch: allow Area Code 0 deletions on Progress/Greenery (index)."""
import os

_FLAG_PATH = os.path.join("Data", "kayakalp_ac0_delete_allowed.flag")


def read_kayakalp_ac0_delete_allowed():
    try:
        with open(_FLAG_PATH, encoding="utf-8") as f:
            return f.read().strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        return False


def write_kayakalp_ac0_delete_allowed(allowed: bool):
    os.makedirs(os.path.dirname(_FLAG_PATH), exist_ok=True)
    with open(_FLAG_PATH, "w", encoding="utf-8") as f:
        f.write("true" if allowed else "false")
