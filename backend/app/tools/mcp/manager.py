"""MCP (Model Context Protocol) session lifecycle manager.

Manages stdio or SSE connections to MCP servers, discovers their tools,
and provides lifecycle hooks for startup/shutdown.
"""

import asyncio
import logging

from app.tools.mcp.adapter import MCPToolAdapter

logger = logging.getLogger(__name__)


class MCPSessionManager:
    """Manages connections to multiple MCP servers.

    Each MCP server runs as a subprocess (or connects via SSE) and exposes
    one or more tools. The manager starts each server, discovers its tools,
    and returns them as a flat list.

    Usage:
        manager = MCPSessionManager(mcp_configs)
        tools = await manager.start_all()
        # ... use tools ...
        await manager.stop_all()
    """

    def __init__(
        self,
        server_configs: list[dict] | None = None,
    ) -> None:
        """Initialize the MCP session manager.

        Args:
            server_configs: List of MCP server configs. Each dict has:
                - name: str — server identifier
                - command: list[str] — command and args to start the server
                - env: dict — environment variables
                - url: str (optional) — SSE URL instead of command
        """
        from app.config import settings

        self.server_configs = server_configs or settings.mcp_servers
        self._adapters: list[MCPToolAdapter] = []

    async def start_all(self) -> list:
        """Connect to all configured MCP servers and discover their tools.

        Returns:
            List of discovered MCP tool wrappers.
        """
        all_tools = []

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
                    logger.warning(
                        f"MCP server '{name}' has no command or url, skipping"
                    )
                    continue

                await adapter.connect()
                self._adapters.append(adapter)

                for tool in adapter.tools:
                    all_tools.append(tool)
                    logger.info(
                        f"Registered MCP tool: {tool.name} from server '{name}'"
                    )

            except Exception as e:
                logger.error(f"Failed to start MCP server '{name}': {e}")

        logger.info(
            f"MCP manager started: {len(all_tools)} tools "
            f"from {len(self._adapters)} servers"
        )
        return all_tools

    async def stop_all(self) -> None:
        """Disconnect all MCP sessions and clean up."""
        for adapter in self._adapters:
            try:
                await adapter.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting MCP adapter: {e}")
        self._adapters.clear()
        logger.info("MCP manager: all sessions stopped")
