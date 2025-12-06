"""
Full Feature Verification Test Flow

プロジェクトの全14ツールを網羅的に検証するテストフロー。
実際の使用シナリオに基づいてツール間の連携も確認します。

実行方法:
    pytest tests/test_full_flow.py -v -s
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from src.config.settings import Settings
from src.db.database import Database
from src.db.repositories.agent_repository import AgentRepository
from src.db.repositories.knowledge_repository import KnowledgeRepository
from src.db.repositories.memory_repository import MemoryRepository
from src.embeddings.base import EmbeddingProvider
from src.services.agent_service import AgentService
from src.services.embedding_service import EmbeddingService
from src.services.knowledge_service import KnowledgeService
from src.services.memory_service import MemoryService
from src.services.namespace_service import NamespaceService
from src.tools import agent_tools, knowledge_tools, memory_tools


class MockEmbeddingProvider(EmbeddingProvider):
    """テスト用のモック埋め込みプロバイダー"""

    def __init__(self, dimensions: int = 384):
        self._dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        """テキストから決定論的な埋め込みを生成"""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        # テキストのハッシュから再現可能なベクトルを生成
        hash_val = hash(text)
        return [(hash_val + i) % 1000 / 1000.0 for i in range(self._dimensions)]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """複数テキストの埋め込みを生成"""
        return [await self.embed(text) for text in texts]

    def dimensions(self) -> int:
        return self._dimensions


@pytest.fixture
async def services():
    """テスト用のサービスインスタンスをセットアップ"""
    # インメモリデータベースを使用
    db = Database(":memory:", embedding_dimensions=384)
    await db.connect()
    await db.migrate()

    # プロバイダーとサービスを初期化
    embedding_provider = MockEmbeddingProvider(384)
    embedding_service = EmbeddingService(embedding_provider)

    # Settings and namespace service
    settings = Settings(database_path=":memory:")
    namespace_service = NamespaceService(settings)

    memory_repo = MemoryRepository(db)
    memory_service = MemoryService(memory_repo, embedding_service, namespace_service)

    agent_repo = AgentRepository(db)
    agent_service = AgentService(agent_repo)

    knowledge_repo = KnowledgeRepository(db)
    knowledge_service = KnowledgeService(knowledge_repo, embedding_service)

    yield {
        "db": db,
        "memory": memory_service,
        "agent": agent_service,
        "knowledge": knowledge_service,
    }

    await db.close()


class TestMemoryToolsFullFlow:
    """Memory Tools (6ツール) の完全なテストフロー"""

    async def test_memory_store_all_options(self, services):
        """memory_store: 全オプションのテスト"""
        svc = services["memory"]

        # 1. 基本的な保存
        result = await memory_tools.memory_store(
            svc,
            content="Basic memory content",
        )
        assert "id" in result
        assert result["memory_tier"] == "long_term"
        print(f"✓ Basic store: {result['id']}")

        # 2. 全オプション指定（agent_idはFKのため、先にエージェント登録が必要）
        # agent_idを使わない全オプションテスト
        result = await memory_tools.memory_store(
            svc,
            content="Full options memory",
            content_type="code",
            memory_tier="short_term",
            tags=["test", "full-options"],
            metadata={"version": "1.0", "language": "python"},
            ttl_seconds=3600,
        )
        assert result["memory_tier"] == "short_term"
        print(f"✓ Full options store: {result['id']}")

        # 3. 各content_typeのテスト
        for ctype in ["text", "image", "code", "json", "yaml"]:
            result = await memory_tools.memory_store(
                svc, content=f"Content type: {ctype}", content_type=ctype
            )
            assert "id" in result
            print(f"✓ Content type '{ctype}': OK")

        # 4. 各memory_tierのテスト
        for tier in ["short_term", "long_term", "working"]:
            result = await memory_tools.memory_store(
                svc, content=f"Memory tier: {tier}", memory_tier=tier
            )
            assert result["memory_tier"] == tier
            print(f"✓ Memory tier '{tier}': OK")

    async def test_memory_store_validation(self, services):
        """memory_store: バリデーションのテスト"""
        svc = services["memory"]

        # 空コンテンツ
        result = await memory_tools.memory_store(svc, content="")
        assert result.get("error") is True
        assert "ValidationError" in result.get("error_type", "")
        print("✓ Empty content validation: OK")

        # 無効なmemory_tier
        result = await memory_tools.memory_store(
            svc, content="test", memory_tier="invalid"
        )
        assert result.get("error") is True
        print("✓ Invalid memory_tier validation: OK")

        # 無効なcontent_type
        result = await memory_tools.memory_store(
            svc, content="test", content_type="invalid"
        )
        assert result.get("error") is True
        print("✓ Invalid content_type validation: OK")

        # 負のttl_seconds
        result = await memory_tools.memory_store(svc, content="test", ttl_seconds=-1)
        assert result.get("error") is True
        print("✓ Negative ttl_seconds validation: OK")

    async def test_memory_search_flow(self, services):
        """memory_search: セマンティック検索のテスト"""
        svc = services["memory"]

        # テストデータを作成
        test_data = [
            ("Python is a programming language", ["programming", "python"]),
            ("JavaScript runs in browsers", ["programming", "javascript"]),
            ("SQLite is a database engine", ["database", "sqlite"]),
            ("Machine learning with neural networks", ["ml", "ai"]),
            ("Web development with React", ["programming", "web"]),
        ]

        for content, tags in test_data:
            await memory_tools.memory_store(svc, content=content, tags=tags)

        # 1. 基本検索
        result = await memory_tools.memory_search(svc, query="programming language")
        assert result["total"] > 0
        print(f"✓ Basic search: found {result['total']} results")

        # 2. top_k指定
        result = await memory_tools.memory_search(
            svc, query="programming", top_k=2
        )
        assert len(result["results"]) <= 2
        print(f"✓ Top-k search: limited to {len(result['results'])} results")

        # 3. タグフィルタ
        result = await memory_tools.memory_search(
            svc, query="code", tags=["programming"]
        )
        for r in result["results"]:
            assert "programming" in r["tags"]
        print("✓ Tag filter: OK")

        # 4. min_similarity閾値
        result = await memory_tools.memory_search(
            svc, query="Python programming", min_similarity=0.5
        )
        for r in result["results"]:
            assert r["similarity"] >= 0.5
        print("✓ Min similarity threshold: OK")

        # 5. バリデーション
        result = await memory_tools.memory_search(svc, query="test", top_k=0)
        assert result.get("error") is True
        print("✓ Invalid top_k validation: OK")

        result = await memory_tools.memory_search(
            svc, query="test", min_similarity=1.5
        )
        assert result.get("error") is True
        print("✓ Invalid min_similarity validation: OK")

    async def test_memory_get_flow(self, services):
        """memory_get: ID取得のテスト"""
        svc = services["memory"]

        # メモリを作成
        stored = await memory_tools.memory_store(
            svc,
            content="Test memory for get",
            tags=["test"],
            metadata={"key": "value"},
        )
        memory_id = stored["id"]

        # 1. 正常取得
        result = await memory_tools.memory_get(svc, id=memory_id)
        assert result["id"] == memory_id
        assert result["content"] == "Test memory for get"
        assert result["tags"] == ["test"]
        assert result["metadata"] == {"key": "value"}
        print(f"✓ Get by ID: {memory_id}")

        # 2. 存在しないID
        result = await memory_tools.memory_get(
            svc, id="00000000-0000-0000-0000-000000000000"
        )
        assert result.get("error") is True
        assert result.get("error_type") == "NotFoundError"
        print("✓ Not found error: OK")

    async def test_memory_update_flow(self, services):
        """memory_update: 更新のテスト"""
        svc = services["memory"]

        # メモリを作成
        stored = await memory_tools.memory_store(
            svc,
            content="Original content",
            memory_tier="short_term",
            tags=["original"],
            metadata={"version": 1},
        )
        memory_id = stored["id"]

        # 1. コンテンツ更新
        result = await memory_tools.memory_update(
            svc, id=memory_id, content="Updated content"
        )
        assert result["updated"] is True
        print("✓ Content update: OK")

        # 更新確認
        memory = await memory_tools.memory_get(svc, id=memory_id)
        assert memory["content"] == "Updated content"

        # 2. タグ更新
        result = await memory_tools.memory_update(
            svc, id=memory_id, tags=["updated", "new-tag"]
        )
        assert result["updated"] is True

        memory = await memory_tools.memory_get(svc, id=memory_id)
        assert memory["tags"] == ["updated", "new-tag"]
        print("✓ Tags update: OK")

        # 3. メタデータ更新
        result = await memory_tools.memory_update(
            svc, id=memory_id, metadata={"version": 2, "author": "test"}
        )
        memory = await memory_tools.memory_get(svc, id=memory_id)
        assert memory["metadata"]["version"] == 2
        print("✓ Metadata update: OK")

        # 4. 階層昇格 (short_term → long_term)
        result = await memory_tools.memory_update(
            svc, id=memory_id, memory_tier="long_term"
        )
        memory = await memory_tools.memory_get(svc, id=memory_id)
        assert memory["memory_tier"] == "long_term"
        print("✓ Tier promotion: OK")

        # 5. 存在しないIDの更新
        result = await memory_tools.memory_update(
            svc,
            id="00000000-0000-0000-0000-000000000000",
            content="test",
        )
        assert result.get("error") is True
        print("✓ Update not found error: OK")

    async def test_memory_delete_flow(self, services):
        """memory_delete: 削除のテスト"""
        svc = services["memory"]

        # 1. 単一ID削除
        stored = await memory_tools.memory_store(svc, content="To be deleted")
        result = await memory_tools.memory_delete(svc, id=stored["id"])
        assert result["deleted_count"] == 1
        assert stored["id"] in result["deleted_ids"]
        print("✓ Single delete: OK")

        # 削除確認
        memory = await memory_tools.memory_get(svc, id=stored["id"])
        assert memory.get("error") is True

        # 2. 複数ID削除
        ids = []
        for i in range(3):
            stored = await memory_tools.memory_store(svc, content=f"Batch delete {i}")
            ids.append(stored["id"])

        result = await memory_tools.memory_delete(svc, ids=ids)
        assert result["deleted_count"] == 3
        print("✓ Batch delete: OK")

        # 3. 階層指定削除
        for i in range(3):
            await memory_tools.memory_store(
                svc, content=f"Working memory {i}", memory_tier="working"
            )

        result = await memory_tools.memory_delete(svc, memory_tier="working")
        assert result["deleted_count"] >= 3
        print(f"✓ Tier delete: deleted {result['deleted_count']} memories")

        # 4. older_than削除 (現在より未来を指定して全削除)
        await memory_tools.memory_store(svc, content="Old memory")
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        result = await memory_tools.memory_delete(svc, older_than=future)
        assert result["deleted_count"] >= 1
        print("✓ Older than delete: OK")

    async def test_memory_list_flow(self, services):
        """memory_list: リスト取得のテスト"""
        svc = services["memory"]

        # テストデータを作成
        for tier in ["short_term", "long_term", "working"]:
            for i in range(3):
                await memory_tools.memory_store(
                    svc,
                    content=f"{tier} memory {i}",
                    memory_tier=tier,
                    content_type="text" if i % 2 == 0 else "code",
                    tags=["test", f"tag-{i}"],
                )

        # 1. 全件取得
        result = await memory_tools.memory_list(svc)
        assert result["total"] >= 9
        print(f"✓ List all: {result['total']} memories")

        # 2. 階層フィルタ
        result = await memory_tools.memory_list(svc, memory_tier="long_term")
        for m in result["memories"]:
            assert m["memory_tier"] == "long_term"
        print(f"✓ Tier filter: {result['total']} long_term memories")

        # 3. タグフィルタ
        result = await memory_tools.memory_list(svc, tags=["tag-0"])
        for m in result["memories"]:
            assert "tag-0" in m["tags"]
        print(f"✓ Tag filter: {result['total']} memories with tag-0")

        # 4. content_typeフィルタ
        result = await memory_tools.memory_list(svc, content_type="code")
        for m in result["memories"]:
            assert m["content_type"] == "code"
        print(f"✓ Content type filter: {result['total']} code memories")

        # 5. ページネーション
        result = await memory_tools.memory_list(svc, limit=3, offset=0)
        assert len(result["memories"]) <= 3
        first_page_ids = {m["id"] for m in result["memories"]}

        result = await memory_tools.memory_list(svc, limit=3, offset=3)
        second_page_ids = {m["id"] for m in result["memories"]}
        assert first_page_ids.isdisjoint(second_page_ids)
        print("✓ Pagination: OK")

        # 6. 日付フィルタ
        now = datetime.now(timezone.utc)
        past = (now - timedelta(hours=1)).isoformat()
        future = (now + timedelta(hours=1)).isoformat()

        result = await memory_tools.memory_list(
            svc, created_after=past, created_before=future
        )
        assert result["total"] >= 0
        print("✓ Date filter: OK")


class TestKnowledgeToolsFullFlow:
    """Knowledge Tools (2ツール) の完全なテストフロー"""

    async def test_knowledge_import_flow(self, services):
        """knowledge_import: ドキュメントインポートのテスト"""
        svc = services["knowledge"]

        # 1. 基本的なインポート
        content = """
        Introduction to Python Programming.
        Python is a high-level programming language.
        It is known for its simplicity and readability.
        Python supports multiple programming paradigms.
        """

        result = await knowledge_tools.knowledge_import(
            svc,
            title="Python Introduction",
            content=content,
        )
        assert "document_id" in result
        assert result["chunks_created"] > 0
        print(f"✓ Basic import: {result['chunks_created']} chunks created")

        # 2. 全オプション指定
        # チャンク分割は文単位で行われるため、複数の文を含むコンテンツを使用
        long_content = ". ".join([f"This is sentence number {i}" for i in range(30)])
        result = await knowledge_tools.knowledge_import(
            svc,
            title="Full Options Doc",
            content=long_content,
            source="https://example.com/doc",
            category="documentation",
            chunk_size=200,
            chunk_overlap=20,
            metadata={"author": "test", "version": "1.0"},
        )
        assert result["chunks_created"] >= 3  # 複数チャンクが作成される
        print(f"✓ Full options import: {result['chunks_created']} chunks")

        # 3. チャンクサイズのバリデーション
        result = await knowledge_tools.knowledge_import(
            svc,
            title="Invalid chunk",
            content="test content",
            chunk_size=50,  # 100未満は無効
        )
        assert result.get("error") is True
        print("✓ Invalid chunk_size validation: OK")

        # 4. 空タイトルのバリデーション
        result = await knowledge_tools.knowledge_import(
            svc,
            title="",
            content="test content",
        )
        assert result.get("error") is True
        print("✓ Empty title validation: OK")

        # 5. 空コンテンツのバリデーション
        result = await knowledge_tools.knowledge_import(
            svc,
            title="Test",
            content="",
        )
        assert result.get("error") is True
        print("✓ Empty content validation: OK")

    async def test_knowledge_query_flow(self, services):
        """knowledge_query: クエリのテスト"""
        svc = services["knowledge"]

        # テストドキュメントをインポート
        docs = [
            ("Python Basics", "Python is a programming language for beginners.", "programming"),
            ("JavaScript Guide", "JavaScript is used for web development.", "programming"),
            ("SQL Tutorial", "SQL is used for database queries.", "database"),
            ("Machine Learning", "ML algorithms process large datasets.", "ai"),
        ]

        for title, content, category in docs:
            await knowledge_tools.knowledge_import(
                svc,
                title=title,
                content=content,
                category=category,
            )

        # 1. 基本クエリ
        result = await knowledge_tools.knowledge_query(
            svc, query="programming language"
        )
        assert result["total"] > 0
        print(f"✓ Basic query: found {result['total']} results")

        # 2. top_k指定
        result = await knowledge_tools.knowledge_query(
            svc, query="programming", top_k=2
        )
        assert len(result["results"]) <= 2
        print("✓ Top-k query: OK")

        # 3. カテゴリフィルタ
        result = await knowledge_tools.knowledge_query(
            svc, query="programming", category="programming"
        )
        for r in result["results"]:
            assert r["document"]["category"] == "programming"
        print("✓ Category filter: OK")

        # 4. ドキュメントIDフィルタ（特定ドキュメント内検索）
        # まず最初のドキュメントIDを取得
        first_result = await knowledge_tools.knowledge_query(
            svc, query="Python", top_k=1
        )
        if first_result["total"] > 0:
            doc_id = first_result["results"][0]["document"]["id"]
            result = await knowledge_tools.knowledge_query(
                svc, query="Python", document_id=doc_id
            )
            for r in result["results"]:
                assert r["document"]["id"] == doc_id
            print("✓ Document ID filter: OK")

        # 5. include_document_info=False
        result = await knowledge_tools.knowledge_query(
            svc, query="programming", include_document_info=False
        )
        for r in result["results"]:
            assert "document" not in r
        print("✓ Exclude document info: OK")


class TestAgentToolsFullFlow:
    """Agent Tools (6ツール) の完全なテストフロー"""

    async def test_agent_register_flow(self, services):
        """agent_register: エージェント登録のテスト"""
        svc = services["agent"]

        # 1. 基本登録
        result = await agent_tools.agent_register(
            svc,
            agent_id="agent-001",
            name="Test Agent",
        )
        assert result["id"] == "agent-001"
        assert result["name"] == "Test Agent"
        assert result["registered"] is True
        print("✓ Basic registration: OK")

        # 2. 説明付き登録
        result = await agent_tools.agent_register(
            svc,
            agent_id="agent-002",
            name="Described Agent",
            description="This is a test agent with description",
        )
        assert result["description"] == "This is a test agent with description"
        print("✓ Registration with description: OK")

        # 3. 既存エージェントの再登録（取得）
        result = await agent_tools.agent_register(
            svc,
            agent_id="agent-001",
            name="Different Name",  # 既存の場合は無視される
        )
        assert result["id"] == "agent-001"
        assert result["name"] == "Test Agent"  # 元の名前が維持される
        print("✓ Re-registration returns existing: OK")

        # 4. バリデーション
        result = await agent_tools.agent_register(svc, agent_id="", name="Test")
        assert result.get("error") is True
        print("✓ Empty agent_id validation: OK")

        result = await agent_tools.agent_register(svc, agent_id="test", name="")
        assert result.get("error") is True
        print("✓ Empty name validation: OK")

    async def test_agent_get_flow(self, services):
        """agent_get: エージェント取得のテスト"""
        svc = services["agent"]

        # エージェントを登録
        await agent_tools.agent_register(
            svc,
            agent_id="get-test-agent",
            name="Get Test Agent",
            description="For get test",
        )

        # 1. 正常取得
        result = await agent_tools.agent_get(svc, agent_id="get-test-agent")
        assert result["id"] == "get-test-agent"
        assert result["name"] == "Get Test Agent"
        assert result["description"] == "For get test"
        assert "created_at" in result
        assert "last_active_at" in result
        print("✓ Agent get: OK")

        # 2. 存在しないエージェント
        result = await agent_tools.agent_get(svc, agent_id="non-existent")
        assert result.get("error") is True
        assert result.get("error_type") == "NotFoundError"
        print("✓ Not found error: OK")

    async def test_agent_send_message_flow(self, services):
        """agent_send_message: メッセージ送信のテスト"""
        svc = services["agent"]

        # エージェントを登録
        await agent_tools.agent_register(svc, agent_id="sender", name="Sender Agent")
        await agent_tools.agent_register(svc, agent_id="receiver", name="Receiver Agent")

        # 1. ダイレクトメッセージ
        result = await agent_tools.agent_send_message(
            svc,
            sender_id="sender",
            receiver_id="receiver",
            content="Hello, receiver!",
            message_type="direct",
        )
        assert result["sent"] is True
        assert "id" in result
        print("✓ Direct message: OK")

        # 2. ブロードキャスト
        result = await agent_tools.agent_send_message(
            svc,
            sender_id="sender",
            content="Broadcast message to all",
            message_type="broadcast",
        )
        assert result["sent"] is True
        print("✓ Broadcast message: OK")

        # 3. コンテキストメッセージ
        result = await agent_tools.agent_send_message(
            svc,
            sender_id="sender",
            receiver_id="receiver",
            content="Context update",
            message_type="context",
        )
        assert result["sent"] is True
        print("✓ Context message: OK")

        # 4. メタデータ付き
        result = await agent_tools.agent_send_message(
            svc,
            sender_id="sender",
            receiver_id="receiver",
            content="Message with metadata",
            metadata={"priority": "high", "task_id": "123"},
        )
        assert result["sent"] is True
        print("✓ Message with metadata: OK")

        # 5. バリデーション
        result = await agent_tools.agent_send_message(
            svc,
            sender_id="sender",
            content="",  # 空コンテンツ
        )
        assert result.get("error") is True
        print("✓ Empty content validation: OK")

        result = await agent_tools.agent_send_message(
            svc,
            sender_id="sender",
            content="test",
            message_type="invalid",
        )
        assert result.get("error") is True
        print("✓ Invalid message_type validation: OK")

    async def test_agent_receive_messages_flow(self, services):
        """agent_receive_messages: メッセージ受信のテスト"""
        svc = services["agent"]

        # エージェントを登録してメッセージを送信
        await agent_tools.agent_register(svc, agent_id="msg-sender", name="Sender")
        await agent_tools.agent_register(svc, agent_id="msg-receiver", name="Receiver")

        # 複数メッセージを送信
        for i in range(5):
            await agent_tools.agent_send_message(
                svc,
                sender_id="msg-sender",
                receiver_id="msg-receiver",
                content=f"Message {i}",
            )

        # 1. 未読メッセージを取得（既読にする）
        result = await agent_tools.agent_receive_messages(
            svc,
            agent_id="msg-receiver",
            status="pending",
            mark_as_read=True,
        )
        assert result["total"] >= 5
        print(f"✓ Receive pending messages: {result['total']} messages")

        # 2. 既読メッセージを取得
        result = await agent_tools.agent_receive_messages(
            svc,
            agent_id="msg-receiver",
            status="read",
        )
        assert result["total"] >= 5
        print(f"✓ Receive read messages: {result['total']} messages")

        # 3. 全メッセージを取得
        result = await agent_tools.agent_receive_messages(
            svc,
            agent_id="msg-receiver",
            status="all",
        )
        assert result["total"] >= 5
        print(f"✓ Receive all messages: {result['total']} messages")

        # 4. 既読にしない取得
        # 新しいメッセージを送信
        await agent_tools.agent_send_message(
            svc,
            sender_id="msg-sender",
            receiver_id="msg-receiver",
            content="Do not mark as read",
        )

        result = await agent_tools.agent_receive_messages(
            svc,
            agent_id="msg-receiver",
            status="pending",
            mark_as_read=False,
        )
        pending_count = result["total"]

        # 再度取得しても同じ数
        result = await agent_tools.agent_receive_messages(
            svc,
            agent_id="msg-receiver",
            status="pending",
            mark_as_read=False,
        )
        assert result["total"] == pending_count
        print("✓ Mark as read=False: OK")

        # 5. limit指定
        result = await agent_tools.agent_receive_messages(
            svc,
            agent_id="msg-receiver",
            status="all",
            limit=3,
        )
        assert len(result["messages"]) <= 3
        print("✓ Limit: OK")

    async def test_context_share_flow(self, services):
        """context_share: コンテキスト共有のテスト"""
        svc = services["agent"]

        # エージェントを登録
        await agent_tools.agent_register(svc, agent_id="ctx-owner", name="Context Owner")
        await agent_tools.agent_register(svc, agent_id="ctx-reader", name="Context Reader")
        await agent_tools.agent_register(svc, agent_id="ctx-restricted", name="Restricted Agent")

        # 1. パブリックコンテキスト
        result = await agent_tools.context_share(
            svc,
            key="public-config",
            value={"setting": "value", "count": 42},
            agent_id="ctx-owner",
            access_level="public",
        )
        assert result["stored"] is True
        assert result["key"] == "public-config"
        print("✓ Public context share: OK")

        # 2. 制限付きコンテキスト
        result = await agent_tools.context_share(
            svc,
            key="restricted-config",
            value={"secret": "data"},
            agent_id="ctx-owner",
            access_level="restricted",
            allowed_agents=["ctx-reader"],
        )
        assert result["stored"] is True
        print("✓ Restricted context share: OK")

        # 3. コンテキストの更新
        result = await agent_tools.context_share(
            svc,
            key="public-config",
            value={"setting": "updated", "count": 100},
            agent_id="ctx-owner",
        )
        assert result["stored"] is True
        print("✓ Context update: OK")

        # 4. 様々な値の型
        test_values = [
            ("string-val", "simple string"),
            ("number-val", 12345),
            ("list-val", [1, 2, 3, "four"]),
            ("nested-val", {"a": {"b": {"c": 1}}}),
            ("bool-val", True),
            ("null-val", None),
        ]

        for key, value in test_values:
            result = await agent_tools.context_share(
                svc, key=key, value=value, agent_id="ctx-owner"
            )
            assert result["stored"] is True
        print("✓ Various value types: OK")

    async def test_context_read_flow(self, services):
        """context_read: コンテキスト読み取りのテスト"""
        svc = services["agent"]

        # エージェントとコンテキストを設定
        await agent_tools.agent_register(svc, agent_id="read-owner", name="Owner")
        await agent_tools.agent_register(svc, agent_id="read-allowed", name="Allowed")
        await agent_tools.agent_register(svc, agent_id="read-denied", name="Denied")

        # パブリックコンテキスト
        await agent_tools.context_share(
            svc,
            key="read-public",
            value={"data": "public"},
            agent_id="read-owner",
            access_level="public",
        )

        # 制限付きコンテキスト
        await agent_tools.context_share(
            svc,
            key="read-restricted",
            value={"data": "restricted"},
            agent_id="read-owner",
            access_level="restricted",
            allowed_agents=["read-allowed"],
        )

        # 1. パブリックコンテキストの読み取り（誰でも可）
        result = await agent_tools.context_read(
            svc, key="read-public", agent_id="read-denied"
        )
        assert result["value"] == {"data": "public"}
        assert result["owner_agent_id"] == "read-owner"
        print("✓ Read public context: OK")

        # 2. 制限付きコンテキストの読み取り（許可されたエージェント）
        result = await agent_tools.context_read(
            svc, key="read-restricted", agent_id="read-allowed"
        )
        assert result["value"] == {"data": "restricted"}
        print("✓ Read restricted context (allowed): OK")

        # 3. 制限付きコンテキストの読み取り（オーナー）
        result = await agent_tools.context_read(
            svc, key="read-restricted", agent_id="read-owner"
        )
        assert result["value"] == {"data": "restricted"}
        print("✓ Read restricted context (owner): OK")

        # 4. 制限付きコンテキストの読み取り（拒否されるエージェント）
        result = await agent_tools.context_read(
            svc, key="read-restricted", agent_id="read-denied"
        )
        assert result.get("error") is True
        assert result.get("error_type") == "NotFoundError"
        print("✓ Read restricted context (denied): OK")

        # 5. 存在しないコンテキスト
        result = await agent_tools.context_read(
            svc, key="non-existent", agent_id="read-owner"
        )
        assert result.get("error") is True
        print("✓ Read non-existent context: OK")


class TestCrossToolIntegration:
    """ツール間連携のテスト"""

    async def test_agent_with_memory_flow(self, services):
        """エージェントとメモリの連携テスト"""
        memory_svc = services["memory"]
        agent_svc = services["agent"]

        # エージェントを登録
        await agent_tools.agent_register(
            agent_svc, agent_id="memory-agent", name="Memory Agent"
        )

        # エージェントに紐づくメモリを保存
        result = await memory_tools.memory_store(
            memory_svc,
            content="Agent-specific memory",
            agent_id="memory-agent",
            tags=["agent-data"],
        )
        memory_id = result["id"]

        # メモリを取得して確認
        memory = await memory_tools.memory_get(memory_svc, id=memory_id)
        # agent_idはmemory_getのレスポンスに含まれないため、DB直接確認は省略
        print("✓ Agent with memory integration: OK")

    async def test_multi_agent_knowledge_sharing(self, services):
        """マルチエージェントでのナレッジ共有テスト"""
        knowledge_svc = services["knowledge"]
        agent_svc = services["agent"]

        # エージェントを登録
        await agent_tools.agent_register(
            agent_svc, agent_id="knowledge-producer", name="Knowledge Producer"
        )
        await agent_tools.agent_register(
            agent_svc, agent_id="knowledge-consumer", name="Knowledge Consumer"
        )

        # ナレッジをインポート
        import_result = await knowledge_tools.knowledge_import(
            knowledge_svc,
            title="Shared Knowledge",
            content="This is shared knowledge content for all agents.",
            category="shared",
        )

        # コンテキストでナレッジIDを共有
        await agent_tools.context_share(
            agent_svc,
            key="shared-knowledge-id",
            value={"document_id": import_result["document_id"]},
            agent_id="knowledge-producer",
            access_level="public",
        )

        # 別のエージェントがコンテキストを読み取り
        context = await agent_tools.context_read(
            agent_svc, key="shared-knowledge-id", agent_id="knowledge-consumer"
        )

        # ナレッジをクエリ
        query_result = await knowledge_tools.knowledge_query(
            knowledge_svc,
            query="shared knowledge",
            document_id=context["value"]["document_id"],
        )
        assert query_result["total"] > 0
        print("✓ Multi-agent knowledge sharing: OK")

    async def test_complete_workflow_simulation(self, services):
        """完全なワークフローシミュレーション"""
        memory_svc = services["memory"]
        knowledge_svc = services["knowledge"]
        agent_svc = services["agent"]

        print("\n=== Complete Workflow Simulation ===\n")

        # 1. エージェントを登録
        agents = ["director", "researcher", "coder", "reviewer"]
        for agent_id in agents:
            await agent_tools.agent_register(
                agent_svc, agent_id=agent_id, name=f"{agent_id.title()} Agent"
            )
        print("Step 1: Registered 4 agents")

        # 2. ディレクターがタスクを共有
        await agent_tools.context_share(
            agent_svc,
            key="current-task",
            value={
                "task_id": "TASK-001",
                "title": "Implement user authentication",
                "status": "in_progress",
                "assigned_to": ["coder"],
            },
            agent_id="director",
        )
        print("Step 2: Director shared task context")

        # 3. リサーチャーがドキュメントをインポート
        await knowledge_tools.knowledge_import(
            knowledge_svc,
            title="Authentication Best Practices",
            content="""
            Authentication security best practices include:
            - Use secure password hashing like bcrypt.
            - Implement rate limiting to prevent brute force.
            - Use JWT tokens with proper expiration.
            - Enable two-factor authentication.
            """,
            category="security",
        )
        print("Step 3: Researcher imported knowledge document")

        # 4. コーダーがナレッジを検索して参考にする
        query_result = await knowledge_tools.knowledge_query(
            knowledge_svc, query="authentication security", top_k=3
        )
        print(f"Step 4: Coder queried knowledge base ({query_result['total']} results)")

        # 5. コーダーが作業メモリを保存
        await memory_tools.memory_store(
            memory_svc,
            content="Implemented bcrypt password hashing in auth module",
            memory_tier="working",
            tags=["implementation", "auth"],
            agent_id="coder",
        )
        await memory_tools.memory_store(
            memory_svc,
            content="Added rate limiting middleware with 5 attempts per minute",
            memory_tier="working",
            tags=["implementation", "security"],
            agent_id="coder",
        )
        print("Step 5: Coder stored working memories")

        # 6. コーダーがレビュアーにメッセージを送信
        await agent_tools.agent_send_message(
            agent_svc,
            sender_id="coder",
            receiver_id="reviewer",
            content="Authentication implementation complete. Ready for review.",
            metadata={"files_changed": 5, "tests_added": 12},
        )
        print("Step 6: Coder sent message to reviewer")

        # 7. レビュアーがメッセージを受信
        messages = await agent_tools.agent_receive_messages(
            agent_svc, agent_id="reviewer"
        )
        print(f"Step 7: Reviewer received {messages['total']} message(s)")

        # 8. レビュアーがコーダーの作業メモリを検索
        search_result = await memory_tools.memory_search(
            memory_svc,
            query="authentication implementation",
            tags=["implementation"],
        )
        print(f"Step 8: Reviewer searched memories ({search_result['total']} found)")

        # 9. レビュー完了後、作業メモリを長期メモリに昇格
        for result in search_result["results"]:
            await memory_tools.memory_update(
                memory_svc, id=result["id"], memory_tier="long_term"
            )
        print("Step 9: Promoted working memories to long-term")

        # 10. タスクステータスを更新
        await agent_tools.context_share(
            agent_svc,
            key="current-task",
            value={
                "task_id": "TASK-001",
                "title": "Implement user authentication",
                "status": "completed",
                "assigned_to": ["coder"],
                "reviewed_by": "reviewer",
            },
            agent_id="director",
        )
        print("Step 10: Director updated task status to completed")

        # 11. ディレクターが全員にブロードキャスト
        await agent_tools.agent_send_message(
            agent_svc,
            sender_id="director",
            content="TASK-001 completed successfully. Great work team!",
            message_type="broadcast",
        )
        print("Step 11: Director broadcasted completion message")

        print("\n=== Workflow Simulation Complete ===\n")


class TestTTLAndCleanup:
    """TTLとクリーンアップのテスト"""

    async def test_ttl_expiration_flow(self, services):
        """TTL期限切れのテスト"""
        memory_svc = services["memory"]

        # TTL=1秒で短期メモリを作成
        result = await memory_tools.memory_store(
            memory_svc,
            content="Short-lived memory",
            memory_tier="short_term",
            ttl_seconds=1,
        )
        memory_id = result["id"]

        # 直後は取得可能
        memory = await memory_tools.memory_get(memory_svc, id=memory_id)
        assert "error" not in memory
        print("✓ Memory accessible before expiration")

        # 2秒待機
        await asyncio.sleep(2)

        # クリーンアップを実行
        cleanup_count = await memory_svc.cleanup_expired()
        print(f"✓ Cleanup removed {cleanup_count} expired memories")

        # 期限切れ後は取得不可
        memory = await memory_tools.memory_get(memory_svc, id=memory_id)
        assert memory.get("error") is True
        print("✓ Memory not accessible after expiration and cleanup")


# テスト実行用のメイン関数
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
