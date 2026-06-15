"""共享的测试夹具。"""

import pytest


@pytest.fixture
def anyio_backend():
    """对所有异步测试使用asyncio。"""
    return "asyncio"
