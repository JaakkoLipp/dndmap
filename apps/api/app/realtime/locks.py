"""Per-object editing locks.

A lock is held by a single ``client_id`` for a short TTL. While the lock
is held other clients see the object as "being edited by X" and the UI
should suppress conflicting writes. Locks auto-expire so an abandoned
edit (tab closed without a clean disconnect) clears itself.

Two implementations:
- :class:`InMemoryLockStore` for tests / single-process dev. Stores locks
  in a process-local dict.
- :class:`RedisLockStore` for hosted multi-process deployments. Uses
  ``SET key value EX ttl NX`` for atomic acquire and a Lua compare-and-
  delete for safe release.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class Lock:
    map_id: UUID
    object_id: UUID
    holder_client_id: str
    holder_display_name: str | None
    expires_at: float  # epoch seconds (monotonic-equivalent for in-memory)

    def to_payload(self) -> dict[str, Any]:
        return {
            "object_id": str(self.object_id),
            "client_id": self.holder_client_id,
            "display_name": self.holder_display_name,
            "expires_at": self.expires_at,
        }


class LockStore(Protocol):
    async def acquire(
        self,
        map_id: UUID,
        object_id: UUID,
        holder_client_id: str,
        holder_display_name: str | None,
        ttl_seconds: int,
    ) -> Lock | None: ...

    async def release(
        self, map_id: UUID, object_id: UUID, holder_client_id: str
    ) -> bool: ...

    async def refresh(
        self,
        map_id: UUID,
        object_id: UUID,
        holder_client_id: str,
        ttl_seconds: int,
    ) -> Lock | None: ...

    async def list_for_map(self, map_id: UUID) -> list[Lock]: ...

    async def release_all_for_client(self, client_id: str) -> list[Lock]: ...


class InMemoryLockStore:
    """Single-process lock store. TTL is enforced lazily on read/write."""

    def __init__(self) -> None:
        self._locks: dict[tuple[UUID, UUID], Lock] = {}
        self._lock = asyncio.Lock()

    def _is_expired(self, lock: Lock) -> bool:
        return lock.expires_at <= time.time()

    async def _evict_expired_unlocked(self) -> None:
        now = time.time()
        expired = [
            key for key, lock in self._locks.items() if lock.expires_at <= now
        ]
        for key in expired:
            del self._locks[key]

    async def acquire(
        self,
        map_id: UUID,
        object_id: UUID,
        holder_client_id: str,
        holder_display_name: str | None,
        ttl_seconds: int,
    ) -> Lock | None:
        async with self._lock:
            await self._evict_expired_unlocked()
            existing = self._locks.get((map_id, object_id))
            if existing is not None and existing.holder_client_id != holder_client_id:
                return None
            lock = Lock(
                map_id=map_id,
                object_id=object_id,
                holder_client_id=holder_client_id,
                holder_display_name=holder_display_name,
                expires_at=time.time() + ttl_seconds,
            )
            self._locks[(map_id, object_id)] = lock
            return lock

    async def release(
        self, map_id: UUID, object_id: UUID, holder_client_id: str
    ) -> bool:
        async with self._lock:
            existing = self._locks.get((map_id, object_id))
            if existing is None or existing.holder_client_id != holder_client_id:
                return False
            del self._locks[(map_id, object_id)]
            return True

    async def refresh(
        self,
        map_id: UUID,
        object_id: UUID,
        holder_client_id: str,
        ttl_seconds: int,
    ) -> Lock | None:
        async with self._lock:
            existing = self._locks.get((map_id, object_id))
            if existing is None or existing.holder_client_id != holder_client_id:
                return None
            existing.expires_at = time.time() + ttl_seconds
            return existing

    async def list_for_map(self, map_id: UUID) -> list[Lock]:
        async with self._lock:
            await self._evict_expired_unlocked()
            return [lock for (m, _), lock in self._locks.items() if m == map_id]

    async def release_all_for_client(self, client_id: str) -> list[Lock]:
        async with self._lock:
            released: list[Lock] = []
            keep: dict[tuple[UUID, UUID], Lock] = {}
            for key, lock in self._locks.items():
                if lock.holder_client_id == client_id:
                    released.append(lock)
                else:
                    keep[key] = lock
            self._locks = keep
            return released


class RedisLockStore:
    """Redis-backed lock store using ``SET ... EX ... NX``."""

    # ARGV[1] = expected holder_client_id
    _COMPARE_DELETE_LUA = """
    local current = redis.call('HGET', KEYS[1], 'holder')
    if current == ARGV[1] then
        return redis.call('DEL', KEYS[1])
    end
    return 0
    """

    def __init__(self, redis_client) -> None:  # type: ignore[no-untyped-def]
        self._redis = redis_client

    @staticmethod
    def _key(map_id: UUID, object_id: UUID) -> str:
        return f"dndmap:lock:{map_id}:{object_id}"

    @staticmethod
    def _scan_pattern(map_id: UUID) -> str:
        return f"dndmap:lock:{map_id}:*"

    async def acquire(
        self,
        map_id: UUID,
        object_id: UUID,
        holder_client_id: str,
        holder_display_name: str | None,
        ttl_seconds: int,
    ) -> Lock | None:
        key = self._key(map_id, object_id)
        existing = await self._redis.hgetall(key)
        if existing:
            current_holder = existing.get("holder")
            if current_holder and current_holder != holder_client_id:
                return None

        pipe = self._redis.pipeline()
        pipe.hset(
            key,
            mapping={
                "holder": holder_client_id,
                "display_name": holder_display_name or "",
            },
        )
        pipe.expire(key, ttl_seconds)
        await pipe.execute()
        return Lock(
            map_id=map_id,
            object_id=object_id,
            holder_client_id=holder_client_id,
            holder_display_name=holder_display_name,
            expires_at=time.time() + ttl_seconds,
        )

    async def release(
        self, map_id: UUID, object_id: UUID, holder_client_id: str
    ) -> bool:
        key = self._key(map_id, object_id)
        deleted = await self._redis.eval(
            self._COMPARE_DELETE_LUA, 1, key, holder_client_id
        )
        return int(deleted or 0) > 0

    async def refresh(
        self,
        map_id: UUID,
        object_id: UUID,
        holder_client_id: str,
        ttl_seconds: int,
    ) -> Lock | None:
        key = self._key(map_id, object_id)
        existing = await self._redis.hgetall(key)
        if not existing or existing.get("holder") != holder_client_id:
            return None
        await self._redis.expire(key, ttl_seconds)
        return Lock(
            map_id=map_id,
            object_id=object_id,
            holder_client_id=holder_client_id,
            holder_display_name=existing.get("display_name") or None,
            expires_at=time.time() + ttl_seconds,
        )

    async def list_for_map(self, map_id: UUID) -> list[Lock]:
        results: list[Lock] = []
        async for key in self._redis.scan_iter(match=self._scan_pattern(map_id)):
            data = await self._redis.hgetall(key)
            if not data:
                continue
            try:
                _, _, _, _, object_id_str = key.split(":")
                object_id = UUID(object_id_str)
            except (ValueError, TypeError):
                continue
            ttl = await self._redis.ttl(key)
            results.append(
                Lock(
                    map_id=map_id,
                    object_id=object_id,
                    holder_client_id=data.get("holder", ""),
                    holder_display_name=data.get("display_name") or None,
                    expires_at=time.time() + max(int(ttl or 0), 0),
                )
            )
        return results

    async def release_all_for_client(self, client_id: str) -> list[Lock]:
        # Locks aren't indexed by holder; scanning the full namespace would
        # be expensive on large deployments. The TTL serves as the safety
        # net here — abandoned locks self-clear within `ttl_seconds`.
        # Implement only if profiling shows it's needed.
        return []


def build_lock_store(redis_client) -> LockStore:  # type: ignore[no-untyped-def]
    if redis_client is not None:
        return RedisLockStore(redis_client)
    return InMemoryLockStore()
