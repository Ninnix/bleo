from typing import Optional


class BleoError(Exception):
    """Base exception for bleo."""


class AuthError(BleoError):
    """Authentication failure (bad or missing key)."""


class RatelimitError(BleoError):
    """HTTP 429 from the server."""

    def __init__(
        self,
        message: str = "",
        *,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message)
        self.retry_after = retry_after


class APIError(BleoError):
    """Any other non-200 response."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        body: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
