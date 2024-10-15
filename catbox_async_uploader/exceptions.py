class CatboxError(Exception):
    """Base exception for Catbox errors."""
    pass


class CatboxFileNotFoundError(CatboxError):
    """Exception raised when a file is not found."""
    pass


class CatboxTimeoutError(CatboxError):
    """Exception raised when the request times out."""
    pass


class CatboxConnectionError(CatboxError):
    """Exception raised when there is a connection error."""
    pass


class CatboxHTTPError(CatboxError):
    """Exception raised for HTTP errors."""
    pass
