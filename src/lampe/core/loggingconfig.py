import logging
import logging.config
import os

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(levelname)s:    %(asctime)s %(module)s %(process)d %(thread)d %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "lampe_sdk": {
            "handlers": ["console"],
            "level": "DEBUG" if os.environ.get("LAMPE_SDK_DEBUG", "").lower() in ("1", "true", "yes") else "INFO",
            "propagate": False,
        },
    },
}

LAMPE_LOGGER_NAME = "lampe_sdk"
LAMPE_PERFORMANCE_LOGGER_NAME = "lampe_sdk.performance"


def init_logging():
    logging.config.dictConfig(LOGGING)
