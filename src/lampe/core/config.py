from .envconfig import init_env
from .loggingconfig import init_logging


def initialize():
    init_env()
    init_logging()


__all__ = ["initialize"]
