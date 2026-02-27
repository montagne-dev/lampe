import os


def is_masking_enabled() -> bool:
    return str(os.getenv("MASKING_ENABLED", "false")).lower() == "true"
