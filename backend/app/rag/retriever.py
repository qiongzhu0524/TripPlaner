"""RAG检索器：协调嵌入 + 向量搜索 + 结果格式化。

RAG管道的主要入口点。代理或服务调用：
    retriever = TravelKnowledgeRetriever(db_session, embedder)
    results = await retriever.retrieve("北京三日游景点推荐", destination="北京")
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.embedder import Embedder
from app.rag.store import KnowledgeVectorStore

logger = logging.getLogger(__name__)


class TravelKnowledgeRetriever:
    """检索相关的旅游知识以丰富代理上下文。

    用法：
        retriever = TravelKnowledgeRetriever(db_session)
        chunks = await retriever.retrieve(
            query="What are the top attractions in Beijing?",
            destination="北京",
            top_k=5,
        )
        # 为代理的系统提示格式化结果：
        context_text = retriever.format_for_context(chunks)
    """

    def __init__(
        self,
        session: AsyncSession,
        embedder: Embedder | None = None,
    ) -> None:
        """初始化检索器。

        参数：
            session: 数据库会话。
            embedder: 可选的Embedder实例（如果未提供则创建一个）。
        """
        self._session = session
        self._store = KnowledgeVectorStore(session)
        self._embedder = embedder or Embedder()

    async def retrieve(
        self,
        query: str,
        destination: str | None = None,
        top_k: int = 5,
        min_similarity: float = 0.5,
    ) -> list[dict[str, Any]]:
        """检索与查询相关的知识块。

        参数：
            query: 自然语言查询。
            destination: 可选的目的地筛选。
            top_k: 最大结果数量。
            min_similarity: 最小余弦相似度阈值。

        返回：
            包含标题、内容、相似度等的块字典列表。
        """
        # 生成查询嵌入
        query_embedding = await self._embedder.embed(query)

        # 搜索向量存储
        results = await self._store.search_similar(
            query_embedding=query_embedding,
            destination=destination,
            top_k=top_k,
        )

        # 按最小相似度筛选
        filtered = [r for r in results if r.get("similarity", 0) >= min_similarity]

        logger.debug(
            f"RAG retrieved {len(filtered)} chunks for query '{query[:50]}...' "
            f"({len(results)} raw, filtered by similarity >= {min_similarity})"
        )

        return filtered

    @staticmethod
    def format_for_context(chunks: list[dict[str, Any]]) -> str:
        """将检索到的块格式化为系统提示的上下文字符串。

        参数：
            chunks: 来自retrieve()的块字典列表。

        返回：
            用于注入代理系统提示的格式化字符串。
        """
        if not chunks:
            return "No relevant travel knowledge found."

        lines = ["## Relevant Travel Knowledge\n"]
        for i, chunk in enumerate(chunks, 1):
            lines.append(f"### {i}. {chunk.get('title', 'Unknown')}")
            lines.append(f"Category: {chunk.get('category', 'N/A')} | "
                        f"Relevance: {chunk.get('similarity', 0):.2f}")
            lines.append(f"{chunk.get('content', '')}\n")

        return "\n".join(lines)

    @property
    def store(self) -> KnowledgeVectorStore:
        """访问底层的向量存储以进行直接操作。"""
        return self._store
