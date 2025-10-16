class GitFileNotFoundError(Exception):
    pass


class GitCommitNotFoundError(Exception):
    pass


class DiffLineRangeNotFoundError(Exception):
    pass


class DiffNotFoundError(Exception):
    pass


class UnableToDeleteError(Exception):
    pass
