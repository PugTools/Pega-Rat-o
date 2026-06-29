import logging
from collections.abc import Iterable
from typing import Any

from neo4j import Driver, GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.core.config import settings


logger = logging.getLogger(__name__)


class Neo4jConnection:
    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
    ) -> None:
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        self.database = database or settings.NEO4J_DATABASE
        self._driver: Driver | None = None

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=300,
                connection_timeout=10,
            )
        return self._driver

    def verify(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except (Neo4jError, ServiceUnavailable, OSError, ValueError) as exc:
            logger.warning("neo4j_connectivity_failed: %s", exc)
            return False

    def execute_query(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
        write: bool = False,
    ) -> list[dict[str, Any]]:
        safe_cypher = _validate_cypher(cypher)
        safe_parameters = _safe_parameters(parameters or {})
        try:
            with self.driver.session(database=self.database) as session:
                runner = session.execute_write if write else session.execute_read
                return runner(self._run_query, safe_cypher, safe_parameters)
        except (Neo4jError, ServiceUnavailable, OSError, ValueError) as exc:
            logger.exception("neo4j_query_failed")
            raise RuntimeError(f"Neo4j query failed: {exc}") from exc

    def execute_write_batch(
        self,
        cypher: str,
        rows: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return self.execute_query(cypher, {"rows": list(rows)}, write=True)

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    @staticmethod
    def _run_query(tx: Any, cypher: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        result = tx.run(cypher, **parameters)
        return [record.data() for record in result]


def _validate_cypher(cypher: str) -> str:
    if not isinstance(cypher, str):
        raise ValueError("Cypher query must be a string.")
    normalized = cypher.strip()
    if not normalized:
        raise ValueError("Cypher query cannot be empty.")
    if ";" in normalized:
        raise ValueError("Cypher multi-statement execution is disabled.")
    return normalized


def _safe_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(parameters, dict):
        raise ValueError("Neo4j parameters must be provided as a mapping.")
    return {
        str(key): _safe_value(value)
        for key, value in parameters.items()
        if key is not None
    }


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list | tuple | set):
        return [_safe_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _safe_value(nested_value)
            for key, nested_value in value.items()
            if key is not None
        }
    return str(value)


neo4j_connection = Neo4jConnection()
