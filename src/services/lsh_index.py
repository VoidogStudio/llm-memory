"""Locality Sensitive Hashing (LSH) index for efficient duplicate detection."""

from typing import Any

try:
    import numpy as np

    LSH_AVAILABLE = True
except ImportError:
    LSH_AVAILABLE = False


class LSHIndex:
    """LSH index for approximate nearest neighbor search.

    Uses Random Projection LSH (SimHash variant) optimized for cosine similarity.
    Reduces duplicate detection complexity from O(N^2) to O(N).
    """

    def __init__(
        self,
        num_hash_tables: int = 10,
        hash_size: int = 16,
        embedding_dim: int = 384,
        seed: int = 42,
    ) -> None:
        """Initialize LSH index.

        Args:
            num_hash_tables: Number of hash tables (precision vs speed tradeoff)
            hash_size: Number of bits per hash
            embedding_dim: Dimension of embedding vectors
            seed: Random seed for reproducibility
        """
        if not LSH_AVAILABLE:
            raise RuntimeError(
                "NumPy is required for LSH index. "
                "Install with: pip install numpy"
            )

        self.num_hash_tables = num_hash_tables
        self.hash_size = hash_size
        self.embedding_dim = embedding_dim

        # Generate random hyperplanes for LSH
        self.random_planes = self._generate_random_planes(seed)

        # Hash tables: hash_value -> set of memory_ids
        self.hash_tables: list[dict[int, set[str]]] = [
            {} for _ in range(num_hash_tables)
        ]

        # Store embeddings for exact similarity calculation
        self.memory_embeddings: dict[str, np.ndarray] = {}

    def _generate_random_planes(self, seed: int) -> list[np.ndarray]:
        """Generate random hyperplanes for LSH.

        Args:
            seed: Random seed

        Returns:
            List of random plane matrices
        """
        rng = np.random.default_rng(seed)
        planes = []
        for _ in range(self.num_hash_tables):
            plane = rng.standard_normal((self.hash_size, self.embedding_dim))
            planes.append(plane)
        return planes

    def _compute_hash(self, embedding: np.ndarray, table_idx: int) -> int:
        """Compute hash value for an embedding.

        Args:
            embedding: Embedding vector
            table_idx: Hash table index

        Returns:
            Hash value (integer)
        """
        # Project embedding onto random planes
        projections = self.random_planes[table_idx] @ embedding

        # Convert to binary hash
        bits = (projections > 0).astype(int)

        # Convert binary to integer
        hash_value = sum(int(bit) << i for i, bit in enumerate(bits))
        return hash_value

    def add(self, memory_id: str, embedding: list[float]) -> None:
        """Add a memory to the LSH index.

        Args:
            memory_id: Memory ID
            embedding: Embedding vector
        """
        emb_array = np.array(embedding, dtype=np.float32)

        # Add to each hash table
        for table_idx in range(self.num_hash_tables):
            hash_value = self._compute_hash(emb_array, table_idx)
            if hash_value not in self.hash_tables[table_idx]:
                self.hash_tables[table_idx][hash_value] = set()
            self.hash_tables[table_idx][hash_value].add(memory_id)

        # Store embedding for exact similarity calculation
        self.memory_embeddings[memory_id] = emb_array

    def remove(self, memory_id: str) -> bool:
        """Remove a memory from the LSH index.

        Args:
            memory_id: Memory ID to remove

        Returns:
            True if removed, False if not found
        """
        if memory_id not in self.memory_embeddings:
            return False

        embedding = self.memory_embeddings[memory_id]

        # Remove from each hash table
        for table_idx in range(self.num_hash_tables):
            hash_value = self._compute_hash(embedding, table_idx)
            if hash_value in self.hash_tables[table_idx]:
                self.hash_tables[table_idx][hash_value].discard(memory_id)
                if not self.hash_tables[table_idx][hash_value]:
                    del self.hash_tables[table_idx][hash_value]

        # Remove embedding
        del self.memory_embeddings[memory_id]
        return True

    def query_candidates(
        self,
        embedding: list[float],
        max_candidates: int = 100,
    ) -> set[str]:
        """Query for similar candidate memories (fast filtering).

        Args:
            embedding: Query embedding vector
            max_candidates: Maximum number of candidates to return

        Returns:
            Set of candidate memory IDs
        """
        emb_array = np.array(embedding, dtype=np.float32)
        candidates: set[str] = set()

        # Collect candidates from all hash tables
        for table_idx in range(self.num_hash_tables):
            hash_value = self._compute_hash(emb_array, table_idx)
            if hash_value in self.hash_tables[table_idx]:
                candidates.update(self.hash_tables[table_idx][hash_value])

        # Limit candidates if needed
        if len(candidates) > max_candidates:
            candidates = set(list(candidates)[:max_candidates])

        return candidates

    def find_similar(
        self,
        embedding: list[float],
        top_k: int = 10,
        min_similarity: float = 0.7,
    ) -> list[tuple[str, float]]:
        """Find similar memories using LSH + exact similarity.

        Args:
            embedding: Query embedding vector
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of (memory_id, similarity) tuples sorted by similarity
        """
        # Get candidates using LSH
        candidates = self.query_candidates(embedding, max_candidates=100)

        if not candidates:
            return []

        # Compute exact cosine similarity for candidates
        emb_array = np.array(embedding, dtype=np.float32)
        emb_norm = np.linalg.norm(emb_array)

        results: list[tuple[str, float]] = []
        for memory_id in candidates:
            candidate_emb = self.memory_embeddings[memory_id]
            candidate_norm = np.linalg.norm(candidate_emb)

            # Cosine similarity
            if emb_norm > 0 and candidate_norm > 0:
                similarity = float(
                    np.dot(emb_array, candidate_emb) / (emb_norm * candidate_norm)
                )
                if similarity >= min_similarity:
                    results.append((memory_id, similarity))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    async def build_index(
        self,
        repository: Any,
        namespace: str | None = None,
    ) -> int:
        """Build LSH index from database.

        Args:
            repository: Memory repository instance
            namespace: Target namespace

        Returns:
            Number of memories indexed
        """
        # Clear existing index
        self.clear()

        # Get all embeddings from repository
        embeddings = await repository.get_all_embeddings(namespace=namespace)

        # Add to index
        for memory_id, embedding in embeddings:
            self.add(memory_id, embedding)

        return len(embeddings)

    def clear(self) -> None:
        """Clear the LSH index."""
        self.hash_tables = [{} for _ in range(self.num_hash_tables)]
        self.memory_embeddings = {}
