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


class ConfigurationError(RepoVitalsError):
    """Raised when project configuration cannot be read."""


class PackageApiError(RepoVitalsError):
    """Raised when package metadata cannot be retrieved."""


class CacheError(RepoVitalsError):
    """Raised when cached data cannot be read or written."""
