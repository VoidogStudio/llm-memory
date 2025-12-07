"""Semantic cache for query results using LSH similarity search."""

import asyncio
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from src.models.context import CacheEntry, CacheStats
from src.services.embedding_service import EmbeddingService
from src.services.lsh_index import LSH_AVAILABLE, LSHIndex


class SemanticCache:
    """Semantic cache for query results with TTL and LRU eviction.

    Uses LSH (Locality Sensitive Hashing) for fast similarity-based
    cache lookups. Falls back to exact match if LSH is not available.
    """

    def __init__(
        self,
        max_size: int,
        ttl_seconds: int,
        embedding_service: EmbeddingService,
        similarity_threshold: float = 0.95,
    ) -> None:
        """Initialize semantic cache.

        Args:
            max_size: Maximum number of cache entries
            ttl_seconds: Time-to-live for cache entries in seconds
            embedding_service: Service for generating query embeddings
            similarity_threshold: Minimum similarity for cache hit (0.0-1.0)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold

        # Cache storage: hash -> CacheEntry
        self.cache: dict[str, CacheEntry] = {}

        # LSH index for similarity search (if available)
        self.lsh_index: LSHIndex | None = None
        if LSH_AVAILABLE:
            try:
                self.lsh_index = LSHIndex(
                    num_hash_tables=10,
                    hash_size=16,
                    embedding_dim=self.embedding_service.provider.dimensions(),
                )
            except Exception:
                # LSH initialization failed, continue without it
                self.lsh_index = None

        # Statistics
        self.hit_count = 0
        self.miss_count = 0

        # Start background cleanup task
        self._cleanup_task: asyncio.Task[None] | None = None
        self._start_cleanup_task()

    def _start_cleanup_task(self) -> None:
        """Start background task for TTL cleanup."""
        try:
            loop = asyncio.get_running_loop()
            self._cleanup_task = loop.create_task(self._cleanup_expired())
        except RuntimeError:
            # No event loop running yet, cleanup will start when needed
            pass

    async def get(
        self,
        query: str,
        namespace: str | None = None,
    ) -> tuple[Any | None, bool]:
        """Get cached result for a query.

        Args:
            query: Search query
            namespace: Optional namespace for cache key

        Returns:
            Tuple of (result or None, cache_hit boolean)
        """
        # Generate query embedding (use is_query=True for search queries)
        query_embedding = await self.embedding_service.generate(query, is_query=True)

        # Generate cache key
        cache_key = self._generate_cache_key(query, namespace)

        # Check for exact match
        if cache_key in self.cache:
            entry = self.cache[cache_key]

            # Check if expired
            if entry.expires_at and datetime.now(timezone.utc) > entry.expires_at:
                # Remove expired entry
                del self.cache[cache_key]
                if self.lsh_index:
                    self.lsh_index.remove(cache_key)
                self.miss_count += 1
                return None, False

            # Update access statistics
            entry.hit_count += 1
            entry.last_accessed = datetime.now(timezone.utc)
            self.hit_count += 1
            return entry.result, True

        # Try LSH similarity search if available
        if self.lsh_index:
            candidates = self.lsh_index.find_similar(
                query_embedding,
                top_k=5,
                min_similarity=self.similarity_threshold,
            )

            for candidate_key, _similarity in candidates:
                if candidate_key in self.cache:
                    entry = self.cache[candidate_key]

                    # Check if expired
                    if entry.expires_at and datetime.now(timezone.utc) > entry.expires_at:
                        continue

                    # Cache hit via similarity
                    entry.hit_count += 1
                    entry.last_accessed = datetime.now(timezone.utc)
                    self.hit_count += 1
                    return entry.result, True

        # Cache miss
        self.miss_count += 1
        return None, False

    async def put(
        self,
        query: str,
        result: Any,
        namespace: str | None = None,
    ) -> None:
        """Store result in cache.

        Args:
            query: Search query
            result: Result to cache
            namespace: Optional namespace for cache key
        """
        # Generate query embedding (use is_query=True for search queries)
        query_embedding = await self.embedding_service.generate(query, is_query=True)

        # Generate cache key
        cache_key = self._generate_cache_key(query, namespace)

        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds)

        # Create cache entry
        entry = CacheEntry(
            query_hash=cache_key,
            query_embedding=query_embedding,
            result=result,
            expires_at=expires_at,
        )

        # Check cache size and evict if needed
        if len(self.cache) >= self.max_size and cache_key not in self.cache:
            self._evict_lru()

        # Store in cache
        self.cache[cache_key] = entry

        # Add to LSH index if available
        if self.lsh_index:
            self.lsh_index.add(cache_key, query_embedding)

    async def invalidate(self, pattern: str | None = None) -> int:
        """Invalidate cache entries.

        Args:
            pattern: Pattern to match for invalidation (None = clear all)

        Returns:
            Number of entries invalidated
        """
        if pattern is None:
            # Clear all
            count = len(self.cache)
            self.cache.clear()
            if self.lsh_index:
                # Recreate LSH index
                if LSH_AVAILABLE:
                    self.lsh_index = LSHIndex(
                        num_hash_tables=10,
                        hash_size=16,
                        embedding_dim=self.embedding_service.provider.dimensions(),
                    )
            return count

        # Pattern-based invalidation
        keys_to_remove = [key for key in self.cache.keys() if pattern in key]
        for key in keys_to_remove:
            del self.cache[key]
            if self.lsh_index:
                self.lsh_index.remove(key)

        return len(keys_to_remove)

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            Cache statistics object
        """
        total_entries = len(self.cache)
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0.0

        # Estimate memory usage
        memory_usage = sys.getsizeof(self.cache)
        for entry in self.cache.values():
            memory_usage += sys.getsizeof(entry.query_hash)
            memory_usage += sys.getsizeof(entry.query_embedding)
            memory_usage += sys.getsizeof(entry.result)

        # Find oldest and newest entries
        oldest_entry: datetime | None = None
        newest_entry: datetime | None = None

        if self.cache:
            entries_by_time = sorted(self.cache.values(), key=lambda e: e.created_at)
            oldest_entry = entries_by_time[0].created_at
            newest_entry = entries_by_time[-1].created_at

        return CacheStats(
            total_entries=total_entries,
            hit_count=self.hit_count,
            miss_count=self.miss_count,
            hit_rate=hit_rate,
            memory_usage_bytes=memory_usage,
            oldest_entry=oldest_entry,
            newest_entry=newest_entry,
        )

    async def _cleanup_expired(self) -> None:
        """Background task to cleanup expired entries."""
        while True:
            try:
                await asyncio.sleep(self.ttl_seconds / 2)

                # Find and remove expired entries
                now = datetime.now(timezone.utc)
                expired_keys = [
                    key
                    for key, entry in self.cache.items()
                    if entry.expires_at and now > entry.expires_at
                ]

                for key in expired_keys:
                    del self.cache[key]
                    if self.lsh_index:
                        self.lsh_index.remove(key)

            except asyncio.CancelledError:
                break
            except Exception:
                # Continue cleanup on errors
                continue

    def _generate_cache_key(self, query: str, namespace: str | None) -> str:
        """Generate cache key from query and namespace.

        Args:
            query: Search query
            namespace: Optional namespace

        Returns:
            SHA256 hash key
        """
        key_string = query
        if namespace:
            key_string = f"{namespace}:{query}"

        return hashlib.sha256(key_string.encode()).hexdigest()

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.cache:
            return

        # Find LRU entry (oldest last_accessed, or oldest created_at if never accessed)
        lru_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].last_accessed or self.cache[k].created_at,
        )

        # Remove from cache and LSH index
        del self.cache[lru_key]
        if self.lsh_index:
            self.lsh_index.remove(lru_key)
