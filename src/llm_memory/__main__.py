"""Entry point for llm-memory MCP server."""

import asyncio

from llm_memory.config.settings import Settings
from llm_memory.server import create_server, initialize_services, shutdown_services


async def main() -> None:
    """Main entry point for the MCP server."""
    # Load settings
    settings = Settings()

    # Initialize services
    await initialize_services(settings)

    # Create and run server
    mcp = create_server()

    try:
        # Run the server (stdio transport)
        # Use run_stdio_async() since we're already in an async context
        await mcp.run_stdio_async()
    finally:
        # Cleanup
        await shutdown_services()


def cli() -> None:
    """CLI entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
