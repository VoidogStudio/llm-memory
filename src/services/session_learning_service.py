"""Session learning service for Auto Knowledge Acquisition."""

import logging

from src.models.acquisition import (
    LearningCategory,
    LearningResult,
    SimilarLearning,
    SourceType,
)
from src.models.memory import ContentType, MemoryTier
from src.services.embedding_service import EmbeddingService
from src.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class SessionLearningService:
    """Service for session learning and knowledge capture."""

    def __init__(
        self,
        memory_service: MemoryService,
        embedding_service: EmbeddingService,
    ) -> None:
        """Initialize session learning service.

        Args:
            memory_service: Memory service
            embedding_service: Embedding service
        """
        self.memory_service = memory_service
        self.embedding_service = embedding_service

    async def learn(
        self,
        content: str,
        category: str,
        context: str | None = None,
        confidence: float = 0.8,
        namespace: str | None = None,
        related_files: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> LearningResult:
        """Learn and record session knowledge.

        Args:
            content: Learning content
            category: Learning category
            context: Additional context
            confidence: Confidence score (0-1)
            namespace: Target namespace
            related_files: Related file paths
            tags: Additional tags

        Returns:
            Learning result

        Raises:
            ValueError: If category is invalid
        """
        # Validate category
        try:
            learning_category = LearningCategory(category)
        except ValueError as e:
            raise ValueError(
                f"Invalid category: {category}. "
                f"Must be one of: {', '.join([c.value for c in LearningCategory])}"
            ) from e

        # Search for similar learnings
        similar_learnings = await self._find_similar_learnings(
            content=content,
            category=learning_category,
            namespace=namespace or "default",
            top_k=5,
        )

        # Determine action based on similarity
        action_taken = "created"
        memory_id: str | None = None

        if similar_learnings:
            highest_similarity = similar_learnings[0].similarity

            # Very high similarity (>= 0.95) - skip or update
            if highest_similarity >= 0.95:
                existing_memory_id = similar_learnings[0].memory_id
                existing_content = similar_learnings[0].content

                # Check if we should update
                if self._should_update_existing(
                    new_content=content,
                    existing_content=existing_content,
                    new_confidence=confidence,
                    existing_confidence=0.8,  # Default for existing
                ):
                    # Update existing memory
                    try:
                        await self.memory_service.update(
                            memory_id=existing_memory_id,
                            content=content,
                        )
                        memory_id = existing_memory_id
                        action_taken = "updated"
                        logger.info(f"Updated existing learning: {existing_memory_id}")
                    except Exception as e:
                        logger.error(f"Error updating memory: {e}")
                        # Fall through to create new
                        pass
                else:
                    # Skip - existing is good enough
                    memory_id = existing_memory_id
                    action_taken = "skipped"
                    logger.info(f"Skipped duplicate learning: {existing_memory_id}")

            # Medium similarity (>= 0.85) - create as complementary
            elif highest_similarity >= 0.85:
                # Create new memory as complementary information
                memory_id = await self._create_learning_memory(
                    content=content,
                    category=learning_category,
                    context=context,
                    confidence=confidence,
                    namespace=namespace,
                    related_files=related_files,
                    tags=tags,
                )
                action_taken = "created"
                logger.info(f"Created complementary learning: {memory_id}")

            # Low similarity (< 0.85) - create new
            else:
                memory_id = await self._create_learning_memory(
                    content=content,
                    category=learning_category,
                    context=context,
                    confidence=confidence,
                    namespace=namespace,
                    related_files=related_files,
                    tags=tags,
                )
                action_taken = "created"

        else:
            # No similar learnings found - create new
            memory_id = await self._create_learning_memory(
                content=content,
                category=learning_category,
                context=context,
                confidence=confidence,
                namespace=namespace,
                related_files=related_files,
                tags=tags,
            )
            action_taken = "created"

        # Ensure we have a memory_id
        if memory_id is None:
            # Fallback: create new memory
            memory_id = await self._create_learning_memory(
                content=content,
                category=learning_category,
                context=context,
                confidence=confidence,
                namespace=namespace,
                related_files=related_files,
                tags=tags,
            )
            action_taken = "created"

        return LearningResult(
            memory_id=memory_id,
            category=learning_category,
            content=content,
            confidence=confidence,
            similar_learnings=similar_learnings,
            action_taken=action_taken,
        )

    async def _find_similar_learnings(
        self,
        content: str,
        category: LearningCategory,
        namespace: str,
        top_k: int = 5,
    ) -> list[SimilarLearning]:
        """Find similar learnings.

        Args:
            content: Content to search for
            category: Learning category
            namespace: Target namespace
            top_k: Maximum number of results

        Returns:
            List of similar learnings
        """
        try:
            # Search for similar memories with same category
            results = await self.memory_service.search(
                query=content,
                namespace=namespace,
                tags=[category.value, "session_learning"],
                top_k=top_k,
            )

            similar_learnings = []
            for result in results:
                # Filter by source type
                if result.memory.metadata.get("source_type") == SourceType.SESSION_LEARNING.value:
                    similar_learnings.append(
                        SimilarLearning(
                            memory_id=result.memory.id,
                            content=result.memory.content,
                            similarity=result.similarity,
                            category=category,
                        )
                    )

            return similar_learnings

        except Exception as e:
            logger.error(f"Error finding similar learnings: {e}")
            return []

    def _should_update_existing(
        self,
        new_content: str,
        existing_content: str,
        new_confidence: float,
        existing_confidence: float,
    ) -> bool:
        """Determine if existing learning should be updated.

        Args:
            new_content: New content
            existing_content: Existing content
            new_confidence: New confidence score
            existing_confidence: Existing confidence score

        Returns:
            True if should update
        """
        # Update if new content is longer (more detailed)
        if len(new_content) > len(existing_content) * 1.2:
            return True

        # Update if new confidence is significantly higher
        if new_confidence > existing_confidence + 0.1:
            return True

        return False

    async def _create_learning_memory(
        self,
        content: str,
        category: LearningCategory,
        context: str | None,
        confidence: float,
        namespace: str | None,
        related_files: list[str] | None,
        tags: list[str] | None,
    ) -> str:
        """Create new learning memory.

        Args:
            content: Learning content
            category: Learning category
            context: Additional context
            confidence: Confidence score
            namespace: Target namespace
            related_files: Related file paths
            tags: Additional tags

        Returns:
            Created memory ID
        """
        # Prepare metadata
        metadata = {
            "source_type": SourceType.SESSION_LEARNING.value,
            "learning_category": category.value,
            "confidence": confidence,
        }

        if context:
            metadata["context"] = context

        if related_files:
            metadata["related_files"] = related_files

        # Prepare tags
        memory_tags = [category.value, "session_learning"]
        if tags:
            memory_tags.extend(tags)

        # Store memory
        memory = await self.memory_service.store(
            content=content,
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.LONG_TERM,
            tags=memory_tags,
            metadata=metadata,
            namespace=namespace,
        )

        logger.info(f"Created learning memory: {memory.id}")
        return memory.id
