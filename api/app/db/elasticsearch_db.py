from elasticsearch import Elasticsearch

from app.core.config import settings


def get_elasticsearch_client() -> Elasticsearch:
    return Elasticsearch(settings.ELASTICSEARCH_URL)


es_client = get_elasticsearch_client()
