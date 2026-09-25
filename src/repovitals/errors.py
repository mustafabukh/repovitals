"""Custom exceptions"""


class RepoVitalsError(Exception):
    """Base class"""


class RepositoryError(RepoVitalsError):
    """repository path cannot be analyzed."""


class GitNotFoundError(RepositoryError):
    """Git is not installed or cannot be found."""


class GitCommandError(RepositoryError):
    """a Git command unsuccessful."""


class GitParseError(RepositoryError):
    """output cannot be parsed."""
