from typing import Any

import httpx

from app.core.config import settings


class IngestionClientError(RuntimeError):
    pass


class BaseIngestionClient:
    default_headers = {
        "Accept": "application/json",
        "User-Agent": "ONGP-PEGA-RATAO/0.1 (+observatorio-gastos-publicos)",
    }

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        verify_ssl: bool | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {**self.default_headers, **(headers or {})}
        self.verify_ssl = settings.HTTP_VERIFY_SSL if verify_ssl is None else verify_ssl

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        url = self._build_url(path)
        request_headers = {**self.headers, **(headers or {})}

        try:
            with httpx.Client(
                timeout=self.timeout,
                headers=request_headers,
                verify=self.verify_ssl,
            ) as client:
                response = client.request(method, url, params=params, json=json)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise IngestionClientError(f"Timeout while requesting {url}") from exc
        except httpx.HTTPStatusError as exc:
            raise IngestionClientError(
                f"HTTP {exc.response.status_code} while requesting {url}"
            ) from exc
        except httpx.RequestError as exc:
            raise IngestionClientError(f"Request failed for {url}: {exc}") from exc

        if not response.content:
            return None

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return response.text

        try:
            return response.json()
        except ValueError as exc:
            raise IngestionClientError(f"Invalid JSON response from {url}") from exc

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        return self.request("GET", path, params=params, headers=headers)

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path

        normalized_path = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{normalized_path}"
