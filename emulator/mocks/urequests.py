"""Mock implementation of MicroPython's urequests module.

Provides HTTP client functionality using Python's requests library.
"""

from emulator import get_state

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


class Response:
    """HTTP response wrapper matching MicroPython's urequests.Response."""

    def __init__(self, requests_response):
        self._response = requests_response
        self.status_code = requests_response.status_code
        self.reason = requests_response.reason
        self.headers = dict(requests_response.headers)
        self._content = None
        self._text = None

    @property
    def content(self) -> bytes:
        """Get response content as bytes."""
        if self._content is None:
            self._content = self._response.content
        return self._content

    @property
    def text(self) -> str:
        """Get response content as text."""
        if self._text is None:
            self._text = self._response.text
        return self._text

    def json(self):
        """Parse response as JSON."""
        return self._response.json()

    def close(self):
        """Close the response."""
        self._response.close()


def request(method: str, url: str, data=None, json=None, headers=None,
            timeout=None, **kwargs) -> Response:
    """Make an HTTP request.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: URL to request
        data: Request body data
        json: JSON data to send
        headers: Request headers
        timeout: Request timeout in seconds

    Returns:
        Response object
    """
    state = get_state()

    if state.get("trace"):
        print(f"[urequests] {method} {url}")

    if not _HAS_REQUESTS:
        raise OSError("requests library not installed")

    # Use real requests library
    resp = _requests.request(
        method=method,
        url=url,
        data=data,
        json=json,
        headers=headers,
        timeout=timeout or 30,
        **kwargs
    )

    return Response(resp)


def get(url: str, **kwargs) -> Response:
    """Make a GET request."""
    return request("GET", url, **kwargs)


def post(url: str, **kwargs) -> Response:
    """Make a POST request."""
    return request("POST", url, **kwargs)


def put(url: str, **kwargs) -> Response:
    """Make a PUT request."""
    return request("PUT", url, **kwargs)


def delete(url: str, **kwargs) -> Response:
    """Make a DELETE request."""
    return request("DELETE", url, **kwargs)


def head(url: str, **kwargs) -> Response:
    """Make a HEAD request."""
    return request("HEAD", url, **kwargs)


def patch(url: str, **kwargs) -> Response:
    """Make a PATCH request."""
    return request("PATCH", url, **kwargs)
