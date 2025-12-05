"""Entry point for llm-memory MCP server."""

import argparse
import asyncio

from llm_memory.config.settings import Settings
from llm_memory.server import create_server, initialize_services, shutdown_services


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="llm-memory",
        description="LLM Memory - Persistent memory and knowledge management for LLMs via MCP",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )
    return parser.parse_args()


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
    # Parse args first (handles --help and --version)
    parse_args()

    # Run the MCP server
    asyncio.run(main())


if __name__ == "__main__":
    cli()
