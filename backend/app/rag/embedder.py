"""RAG管道的嵌入模型抽象。

支持：
- OpenAI text-embedding-3-small（通过API）
- 本地嵌入模型（sentence-transformers的占位实现）
- 缓存嵌入以避免重复计算
"""

import logging
from typing import Any

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class Embedder:
    """生成文本块的向量嵌入。

    默认使用OpenAI的嵌入API。可以扩展以支持
    本地模型（如sentence-transformers）用于离线/隔离环境使用。

    用法：
        embedder = Embedder()
        vector = await embedder.embed("北京故宫是明清两代的皇家宫殿...")
        vectors = await embedder.embed_batch(["text1", "text2", ...])
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
    ) -> None:
        """初始化嵌入器。

        参数：
            model: 嵌入模型名称。
            dimensions: 输出向量维度（text-embedding-3-small为1536）。
        """
        self._model = model
        self._dimensions = dimensions
        self._client: AsyncOpenAI | None = None
        self._cache: dict[str, list[float]] = {}

    @property
    def client(self) -> AsyncOpenAI:
        """延迟初始化OpenAI客户端。"""
        if self._client is None:
            import os

            cfg = settings.llm_openai
            self._client = AsyncOpenAI(
                api_key=cfg.api_key or os.getenv("OPENAI_API_KEY"),
                base_url=cfg.base_url or None,
            )
        return self._client

    async def embed(self, text: str) -> list[float]:
        """为单个文本生成嵌入。

        参数：
            text: 输入文本。

        返回：
            浮点数列表（嵌入向量）。
        """
        # 检查缓存
        cache_key = f"{self._model}:{hash(text)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            response = await self.client.embeddings.create(
                model=self._model,
                input=text,
                dimensions=self._dimensions,
            )
            embedding = response.data[0].embedding
            self._cache[cache_key] = embedding
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # 返回零向量作为回退
            return [0.0] * self._dimensions

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """为多个文本生成嵌入。

        参数：
            texts: 输入文本列表。

        返回：
            嵌入向量列表。
        """
        uncached = []
        uncached_indices = []
        results: list[list[float] | None] = [None] * len(texts)

        # 检查缓存
        for i, text in enumerate(texts):
            cache_key = f"{self._model}:{hash(text)}"
            if cache_key in self._cache:
                results[i] = self._cache[cache_key]
            else:
                uncached.append(text)
                uncached_indices.append(i)

        if not uncached:
            return results  # type: ignore[return-value]

        # 批量嵌入未缓存的文本
        try:
            response = await self.client.embeddings.create(
                model=self._model,
                input=uncached,
                dimensions=self._dimensions,
            )
            for j, data in enumerate(response.data):
                idx = uncached_indices[j]
                cache_key = f"{self._model}:{hash(uncached[j])}"
                self._cache[cache_key] = data.embedding
                results[idx] = data.embedding
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            for idx in uncached_indices:
                if results[idx] is None:
                    results[idx] = [0.0] * self._dimensions

        return results  # type: ignore[return-value]

    @property
    def dimensions(self) -> int:
        """返回嵌入向量维度。"""
        return self._dimensions
