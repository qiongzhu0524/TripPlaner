"""用于RAG的知识库加载器。

从Markdown文件中加载旅游指南文档，将其分割成块，
并在pgvector中建立索引以便检索。

分块策略：
- 按 ## 标题分割（每个部分成为一个块）
- 每个块包含其标题路径以提供上下文
- 最小块大小：50个字符（跳过太小的部分）
"""

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeChunk:
    """知识库内容的单个块。"""

    id: str
    title: str  # Heading path, e.g., "北京 > 景点 > 故宫"
    content: str
    destination: str  # 例如："北京"
    category: str  # 例如："景点"、"餐饮"、"交通"
    source_file: str = ""
    embedding: list[float] | None = None


class MarkdownKnowledgeLoader:
    """加载并对Markdown知识库文件进行分块。

    期望的文件格式：
        # 北京
        ## 景点
        ### 故宫
        故宫是明清两代的皇家宫殿...
        ### 长城
        八达岭长城位于...

    每个 ### 部分成为一个块。父级的 ## 和 # 标题
    提供目的地和类别上下文。

    用法：
        loader = MarkdownKnowledgeLoader("backend/data/knowledge/")
        chunks = loader.load_all()
    """

    def __init__(self, knowledge_dir: str) -> None:
        """使用知识库目录路径初始化。

        参数：
            knowledge_dir: 包含.md文件的目录路径。
        """
        self._dir = knowledge_dir

    def load_all(self) -> list[KnowledgeChunk]:
        """加载知识库目录中的所有Markdown文件并进行分块。

        返回：
            准备好进行嵌入和存储的KnowledgeChunk对象列表。
        """
        all_chunks: list[KnowledgeChunk] = []

        if not os.path.isdir(self._dir):
            logger.warning(f"Knowledge directory not found: {self._dir}")
            return all_chunks

        for filename in sorted(os.listdir(self._dir)):
            if not filename.endswith(".md"):
                continue

            filepath = os.path.join(self._dir, filename)
            try:
                chunks = self._parse_file(filepath)
                all_chunks.extend(chunks)
                logger.info(f"Loaded {len(chunks)} chunks from {filename}")
            except Exception as e:
                logger.error(f"Failed to load {filename}: {e}")

        logger.info(f"Total knowledge chunks loaded: {len(all_chunks)}")
        return all_chunks

    def _parse_file(self, filepath: str) -> list[KnowledgeChunk]:
        """将单个Markdown文件解析为知识块。

        参数：
            filepath: .md文件的路径。

        返回：
            从文件中提取的块列表。
        """
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        filename = os.path.basename(filepath)
        lines = content.split("\n")

        chunks: list[KnowledgeChunk] = []
        current_destination = ""
        current_category = ""
        current_title = ""
        current_content: list[str] = []
        chunk_idx = 0

        def _flush() -> None:
            nonlocal chunk_idx
            if current_content and current_title:
                text = "\n".join(current_content).strip()
                if len(text) >= 50:  # 最小块大小
                    chunk_idx += 1
                    chunks.append(KnowledgeChunk(
                        id=f"{filename}:{chunk_idx}",
                        title=current_title,
                        content=text,
                        destination=current_destination,
                        category=current_category,
                        source_file=filename,
                    ))
                current_content.clear()

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("# ") and not stripped.startswith("## "):
                # 一级标题：目的地
                _flush()
                current_destination = stripped[2:].strip()

            elif stripped.startswith("## ") and not stripped.startswith("### "):
                # 二级标题：类别
                _flush()
                current_category = stripped[3:].strip()
                current_title = f"{current_destination} > {current_category}"

            elif stripped.startswith("### "):
                # 三级标题：具体主题 → 新块
                _flush()
                topic = stripped[4:].strip()
                current_title = f"{current_destination} > {current_category} > {topic}"

            elif stripped:
                current_content.append(stripped)

        # 刷新最后一个块
        _flush()

        return chunks
