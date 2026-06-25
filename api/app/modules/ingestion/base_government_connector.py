import csv
import importlib
import io
import json
import logging
import tempfile
import time
import zipfile
from abc import ABC
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings


logger = logging.getLogger(__name__)

REGISTRY_PATH = Path(__file__).with_name("sources_registry.json")


class GovernmentConnectorError(RuntimeError):
    pass


@dataclass(frozen=True)
class RateLimitConfig:
    requests_per_minute: int = 60
    burst: int = 1


@dataclass(frozen=True)
class RetryConfig:
    attempts: int = 3
    backoff_seconds: float = 1.0
    retry_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)


@dataclass(frozen=True)
class SourceConfig:
    key: str
    name: str
    base_url: str
    source_type: str
    destination_model: str
    enabled: bool = True
    auth_header: str | None = None
    auth_env: str | None = None
    default_params: dict[str, Any] = field(default_factory=dict)
    endpoints: dict[str, str] = field(default_factory=dict)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    csv_delimiter: str = ";"
    encoding: str = "utf-8"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceConfig":
        return cls(
            key=str(payload["key"]),
            name=str(payload["name"]),
            base_url=str(payload["base_url"]).rstrip("/"),
            source_type=str(payload.get("source_type", "json")),
            destination_model=str(payload["destination_model"]),
            enabled=bool(payload.get("enabled", True)),
            auth_header=payload.get("auth_header"),
            auth_env=payload.get("auth_env"),
            default_params=dict(payload.get("default_params") or {}),
            endpoints=dict(payload.get("endpoints") or {}),
            rate_limit=RateLimitConfig(**dict(payload.get("rate_limit") or {})),
            retry=RetryConfig(**dict(payload.get("retry") or {})),
            csv_delimiter=str(payload.get("csv_delimiter", ";")),
            encoding=str(payload.get("encoding", "utf-8")),
        )


class ConnectorRateLimiter:
    def __init__(self, config: RateLimitConfig) -> None:
        self.config = config
        self._last_request_at = 0.0

    def wait(self) -> None:
        if self.config.requests_per_minute <= 0:
            return

        min_interval = 60.0 / self.config.requests_per_minute
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_at = time.monotonic()


class BaseGovernmentConnector(ABC):
    default_headers = {
        "Accept": "application/json,text/csv,application/zip,*/*",
        "User-Agent": "ONGP-PEGA-RATAO/1.0 (+observatorio-gastos-publicos)",
    }

    def __init__(
        self,
        config: SourceConfig,
        timeout: float = 120.0,
        verify_ssl: bool | None = None,
    ) -> None:
        if not config.enabled:
            raise GovernmentConnectorError(f"Fonte desativada: {config.key}")

        self.config = config
        self.timeout = timeout
        self.verify_ssl = settings.HTTP_VERIFY_SSL if verify_ssl is None else verify_ssl
        self.rate_limiter = ConnectorRateLimiter(config.rate_limit)
        self.model_class = self._load_model_class(config.destination_model)

    def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        url = self._build_url(endpoint)
        request_headers = {**self.default_headers, **self._auth_headers(), **(headers or {})}
        request_params = {**self.config.default_params, **(params or {})}

        last_error: Exception | None = None
        for attempt in range(1, self.config.retry.attempts + 1):
            self.rate_limiter.wait()
            try:
                with httpx.Client(
                    timeout=self.timeout,
                    headers=request_headers,
                    verify=self.verify_ssl,
                    follow_redirects=True,
                ) as client:
                    response = client.request(method, url, params=request_params)
                if response.status_code in self.config.retry.retry_status_codes:
                    raise GovernmentConnectorError(
                        f"HTTP {response.status_code} em {url}"
                    )
                response.raise_for_status()
                return response
            except (httpx.HTTPError, GovernmentConnectorError) as exc:
                last_error = exc
                if attempt >= self.config.retry.attempts:
                    break
                sleep_for = self.config.retry.backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "government_connector_retry",
                    extra={
                        "source": self.config.key,
                        "attempt": attempt,
                        "sleep_for": sleep_for,
                        "error": str(exc),
                    },
                )
                time.sleep(sleep_for)

        raise GovernmentConnectorError(
            f"Falha ao coletar {self.config.key} em {url}: {last_error}"
        )

    def fetch_json_items(
        self,
        endpoint_name: str = "default",
        params: dict[str, Any] | None = None,
        path_params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        response = self.request(
            "GET",
            self._endpoint(endpoint_name, path_params=path_params),
            params=params,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise GovernmentConnectorError(
                f"Resposta JSON invalida para {self.config.key}"
            ) from exc
        return self._items(payload)

    def iter_csv_rows(
        self,
        endpoint_name: str = "default",
        params: dict[str, Any] | None = None,
        path_params: dict[str, Any] | None = None,
        delimiter: str | None = None,
        encoding: str | None = None,
    ) -> Iterator[dict[str, str]]:
        response = self.request(
            "GET",
            self._endpoint(endpoint_name, path_params=path_params),
            params=params,
        )
        text_stream = io.StringIO(response.content.decode(encoding or self.config.encoding))
        yield from csv.DictReader(text_stream, delimiter=delimiter or self.config.csv_delimiter)

    def iter_zip_csv_rows(
        self,
        endpoint_name: str = "default",
        params: dict[str, Any] | None = None,
        path_params: dict[str, Any] | None = None,
        csv_name_contains: str | None = None,
        delimiter: str | None = None,
        encoding: str | None = None,
        spool_limit_mb: int = 256,
    ) -> Iterator[dict[str, str]]:
        response = self.request(
            "GET",
            self._endpoint(endpoint_name, path_params=path_params),
            params=params,
        )
        with tempfile.SpooledTemporaryFile(max_size=spool_limit_mb * 1024 * 1024) as buffer:
            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                buffer.write(chunk)
            buffer.seek(0)
            with zipfile.ZipFile(buffer) as archive:
                for member_name in archive.namelist():
                    if not member_name.lower().endswith(".csv"):
                        continue
                    if csv_name_contains and csv_name_contains.lower() not in member_name.lower():
                        continue
                    with archive.open(member_name) as raw_file:
                        text_file = io.TextIOWrapper(
                            raw_file,
                            encoding=encoding or self.config.encoding,
                            newline="",
                        )
                        yield from csv.DictReader(
                            text_file,
                            delimiter=delimiter or self.config.csv_delimiter,
                        )

    def validate_items(self, rows: Iterable[dict[str, Any]]) -> Iterator[BaseModel]:
        for row in rows:
            try:
                yield self.model_class.model_validate(row)
            except ValidationError as exc:
                logger.warning(
                    "government_connector_validation_failed",
                    extra={"source": self.config.key, "error": str(exc)[:500]},
                )

    def _build_url(self, endpoint: str) -> str:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        normalized = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{self.config.base_url}{normalized}"

    def _endpoint(
        self,
        endpoint_name: str,
        path_params: dict[str, Any] | None = None,
    ) -> str:
        try:
            endpoint = self.config.endpoints[endpoint_name]
        except KeyError as exc:
            raise GovernmentConnectorError(
                f"Endpoint '{endpoint_name}' nao configurado para {self.config.key}"
            ) from exc
        return endpoint.format(**(path_params or {}))

    def _auth_headers(self) -> dict[str, str]:
        if not self.config.auth_header or not self.config.auth_env:
            return {}
        token = getattr(settings, self.config.auth_env, None)
        if not token:
            return {}
        return {self.config.auth_header: str(token)}

    def _items(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("data", "dados", "items", "resultado", "content", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            return [payload]
        return []

    def _load_model_class(self, dotted_path: str) -> type[BaseModel]:
        module_name, _, class_name = dotted_path.rpartition(".")
        if not module_name or not class_name:
            raise GovernmentConnectorError(f"Modelo invalido: {dotted_path}")
        module = importlib.import_module(module_name)
        model_class = getattr(module, class_name)
        if not issubclass(model_class, BaseModel):
            raise GovernmentConnectorError(f"Modelo nao e Pydantic: {dotted_path}")
        return model_class


class RegistryGovernmentConnector(BaseGovernmentConnector):
    pass


def load_sources_registry(path: Path = REGISTRY_PATH) -> dict[str, SourceConfig]:
    with path.open("r", encoding="utf-8") as registry_file:
        payload = json.load(registry_file)

    sources = payload.get("sources", [])
    return {
        source_config.key: source_config
        for source_config in (SourceConfig.from_dict(item) for item in sources)
    }


def build_connector(
    source_key: str,
    registry: dict[str, SourceConfig] | None = None,
) -> RegistryGovernmentConnector:
    sources = registry or load_sources_registry()
    try:
        config = sources[source_key]
    except KeyError as exc:
        raise GovernmentConnectorError(f"Fonte nao registrada: {source_key}") from exc
    return RegistryGovernmentConnector(config=config)
