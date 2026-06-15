"""使用pgvector的RAG知识块向量存储。

需要pgvector PostgreSQL扩展：
    CREATE EXTENSION IF NOT EXISTS vector;

创建包含以下字段的knowledge_chunks表：
- id, title, content, destination, category
- embedding: vector(1536)用于相似度搜索
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

logger = logging.getLogger(__name__)


class KnowledgeChunkRecord(Base):
    """带有向量嵌入的知识库块数据库记录。"""

    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    destination: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(128), index=True, default="")
    source_file: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # 嵌入列在pgvector扩展启用后通过原生SQL添加：
    # ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS embedding vector(1536);


class KnowledgeVectorStore:
    """管理包含pgvector相似度搜索的knowledge_chunks表。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._embedding_dim = 1536

    async def create_extension(self) -> None:
        """创建pgvector扩展（如果不存在）。"""
        await self._session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await self._session.flush()
        logger.info("pgvector extension ensured")

    async def add_chunk(
        self,
        title: str,
        content: str,
        destination: str,
        category: str = "",
        source_file: str = "",
        embedding: list[float] | None = None,
    ) -> KnowledgeChunkRecord:
        """插入一个知识块，可选附带嵌入。

        参数：
            title: 块标题/标题路径。
            content: 块文本内容。
            destination: 目的地城市/地区。
            category: 内容类别。
            source_file: 源Markdown文件名。
            embedding: 预先计算的向量嵌入。

        返回：
            已创建的KnowledgeChunkRecord。
        """
        record = KnowledgeChunkRecord(
            title=title,
            content=content,
            destination=destination,
            category=category,
            source_file=source_file,
        )
        self._session.add(record)
        await self._session.flush()

        # 通过原生SQL设置嵌入（SQLAlchemy ORM没有原生向量类型）
        if embedding:
            embedding_str = f"[{','.join(str(v) for v in embedding)}]"
            await self._session.execute(
                text(
                    "UPDATE knowledge_chunks SET embedding = :embedding WHERE id = :id"
                ),
                {"embedding": embedding_str, "id": record.id},
            )
            await self._session.flush()

        return record

    async def search_similar(
        self,
        query_embedding: list[float],
        destination: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        """搜索与查询嵌入相似的块。

        使用余弦距离进行相似度计算。可选地按目的地筛选。

        参数：
            query_embedding: 查询向量。
            destination: 可选的目的地筛选。
            top_k: 结果数量。

        返回：
            包含标题、内容、目的地、相似度的字典列表。
        """
        embedding_str = f"[{','.join(str(v) for v in query_embedding)}]"

        if destination:
            query = text(
                """
                SELECT id, title, content, destination, category,
                       1 - (embedding <=> :embedding) AS similarity
                FROM knowledge_chunks
                WHERE destination = :destination
                ORDER BY embedding <=> :embedding
                LIMIT :limit
                """
            )
            params = {
                "embedding": embedding_str,
                "destination": destination,
                "limit": top_k,
            }
        else:
            query = text(
                """
                SELECT id, title, content, destination, category,
                       1 - (embedding <=> :embedding) AS similarity
                FROM knowledge_chunks
                ORDER BY embedding <=> :embedding
                LIMIT :limit
                """
            )
            params = {"embedding": embedding_str, "limit": top_k}

        result = await self._session.execute(query, params)
        rows = result.fetchall()

        return [
            {
                "id": str(row[0]),
                "title": row[1],
                "content": row[2],
                "destination": row[3],
                "category": row[4],
                "similarity": round(float(row[5]), 4) if row[5] else 0.0,
            }
            for row in rows
        ]

    async def clear_destination(self, destination: str) -> int:
        """移除某个目的地的所有块。返回删除的数量。"""
        result = await self._session.execute(
            text("DELETE FROM knowledge_chunks WHERE destination = :dest RETURNING id"),
            {"dest": destination},
        )
        rows = result.fetchall()
        await self._session.flush()
        logger.info(f"Cleared {len(rows)} chunks for destination '{destination}'")
        return len(rows)
