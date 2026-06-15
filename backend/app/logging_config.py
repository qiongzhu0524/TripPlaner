"""结构化日志配置。"""

import logging
import sys
from datetime import datetime, timezone


def setup_logging(level: str = "INFO") -> None:
    """配置应用程序的结构化日志。"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # 静默嘈杂的第三方日志记录器
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("mcp").setLevel(logging.INFO)
