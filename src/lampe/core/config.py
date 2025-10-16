from .envconfig import init_env


def initialize():
    init_env()


__all__ = ["initialize"]
