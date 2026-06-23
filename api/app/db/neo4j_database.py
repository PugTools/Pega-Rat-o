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
        except (Neo4jError, ServiceUnavailable, OSError) as exc:
            logger.warning("neo4j_connectivity_failed: %s", exc)
            return False

    def execute_query(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
        write: bool = False,
    ) -> list[dict[str, Any]]:
        try:
            with self.driver.session(database=self.database) as session:
                runner = session.execute_write if write else session.execute_read
                return runner(self._run_query, cypher, parameters or {})
        except (Neo4jError, ServiceUnavailable, OSError) as exc:
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


neo4j_connection = Neo4jConnection()
