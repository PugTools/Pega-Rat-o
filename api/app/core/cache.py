import json
from typing import Any

import redis

from app.core.config import settings


redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_json_cache(key: str) -> Any | None:
    try:
        payload = redis_client.get(key)
    except redis.RedisError:
        return None
    if payload is None:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        delete_cache(key)
        return None


def set_json_cache(key: str, value: Any, ttl_seconds: int = 600) -> None:
    try:
        redis_client.setex(key, ttl_seconds, json.dumps(value, default=str))
    except redis.RedisError:
        return


def delete_cache(key: str) -> None:
    try:
        redis_client.delete(key)
    except redis.RedisError:
        return


def delete_pattern(pattern: str) -> None:
    try:
        keys = list(redis_client.scan_iter(pattern))
        if keys:
            redis_client.delete(*keys)
    except redis.RedisError:
        return
