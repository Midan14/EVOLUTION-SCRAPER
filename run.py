#!/usr/bin/env python3
"""
Evolution Gaming Baccarat Scraper - Main Entry Point

Runs the scraper and optionally the API server
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import config


async def run_scraper_only():
    """Run only the scraper"""
    from scraper import EvolutionScraper
    scraper = EvolutionScraper()
    await scraper.run()


async def run_scraper_with_api():
    """Run scraper and API server together"""
    import uvicorn

    from api_server import app
    from database import db
    from scraper import EvolutionScraper

    # Initialize database
    await db.connect()

    # Create scraper
    scraper = EvolutionScraper()

    # Create API server config
    api_config = uvicorn.Config(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        log_level="info"
    )
    api_server = uvicorn.Server(api_config)

    # Run both concurrently
    print("=" * 60)
    print("🎰 EVOLUTION SCRAPER + API SERVER")
    print("=" * 60)
    print(f"API Server: http://{config.API_HOST}:{config.API_PORT}")
    print(f"API Docs: http://{config.API_HOST}:{config.API_PORT}/docs")
    print(f"Target Game: {config.GAME_URL}")
    print("=" * 60)

    await asyncio.gather(
        scraper.run(),
        api_server.serve()
    )


def run_api_only():
    """Run only the API server (for serving existing data)"""
    import uvicorn

    from api_server import app

    print("=" * 60)
    print("🌐 API SERVER ONLY")
    print("=" * 60)
    print(f"Server: http://{config.API_HOST}:{config.API_PORT}")
    print(f"Docs: http://{config.API_HOST}:{config.API_PORT}/docs")
    print("=" * 60)

    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        log_level="info"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Evolution Gaming Baccarat Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                    # Run scraper + API server
  python run.py --scraper-only     # Run only the scraper
  python run.py --api-only         # Run only the API server
  python run.py --headless         # Run in headless mode (no browser window)
        """
    )

    parser.add_argument(
        "--scraper-only",
        action="store_true",
        help="Run only the scraper without API server"
    )

    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Run only the API server (serve existing data)"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )

    args = parser.parse_args()

    # Override headless setting if flag is passed
    if args.headless:
        import os
        os.environ["HEADLESS"] = "true"

    if args.api_only:
        run_api_only()
    elif args.scraper_only:
        asyncio.run(run_scraper_only())
    else:
        asyncio.run(run_scraper_with_api())


if __name__ == "__main__":
    main()
