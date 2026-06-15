"""MCP (Model Context Protocol) session lifecycle manager.

Manages stdio or SSE connections to MCP servers, discovers their tools,
and provides lifecycle hooks for startup/shutdown.
"""

import asyncio
import logging
from typing import Any

from app.tools.mcp.adapter import MCPToolAdapter
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPSessionManager:
    """Manages connections to multiple MCP servers.

    Each MCP server runs as a subprocess (or connects via SSE) and exposes
    one or more tools. The manager starts each server, discovers its tools,
    wraps them as ToolProtocol adapters, and registers them in the ToolRegistry.

    Usage:
        manager = MCPSessionManager(registry, mcp_configs)
        await manager.start_all()
        # ... tools are now available ...
        await manager.stop_all()
    """

    def __init__(
        self,
        registry: ToolRegistry,
        server_configs: list[dict] | None = None,
    ) -> None:
        """Initialize the MCP session manager.

        Args:
            registry: The ToolRegistry to register discovered tools into.
            server_configs: List of MCP server configs. Each dict has:
                - name: str — server identifier
                - command: list[str] — command and args to start the server
                - env: dict — environment variables
                - url: str (optional) — SSE URL instead of command
        """
        from app.config import settings

        self.registry = registry
        self.server_configs = server_configs or settings.mcp_servers
        self._adapters: list[MCPToolAdapter] = []
        self._processes: list[asyncio.subprocess.Process] = []

    async def start_all(self) -> list[str]:
        """Connect to all configured MCP servers and register their tools.

        Returns:
            List of tool names that were registered.
        """
        registered: list[str] = []

        for server_cfg in self.server_configs:
            name = server_cfg.get("name", "unknown")
            command = server_cfg.get("command")
            url = server_cfg.get("url")
            env = server_cfg.get("env", {})

            try:
                if url:
                    adapter = MCPToolAdapter.from_sse(
                        server_name=name,
                        url=url,
                        env=env,
                    )
                elif command:
                    adapter = MCPToolAdapter.from_stdio(
                        server_name=name,
                        command=command,
                        env=env,
                    )
                else:
                    logger.warning(f"MCP server '{name}' has no command or url, skipping")
                    continue

                await adapter.connect()
                self._adapters.append(adapter)

                # Register each discovered tool
                for tool in adapter.tools:
                    self.registry.register(tool)
                    registered.append(tool.name)
                    logger.info(f"Registered MCP tool: {tool.name} from server '{name}'")

            except Exception as e:
                logger.error(f"Failed to start MCP server '{name}': {e}")

        logger.info(f"MCP manager started: {len(registered)} tools from {len(self._adapters)} servers")
        return registered

    async def stop_all(self) -> None:
        """Disconnect all MCP sessions and clean up."""
        for adapter in self._adapters:
            try:
                await adapter.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting MCP adapter: {e}")
        self._adapters.clear()
        logger.info("MCP manager: all sessions stopped")
