"""CLI entrypoint for Finviz data collection (cron-ready)."""

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

from src.constants import VALID_WORKSHEETS
from src.data_collector import CollectorConfig, DataCollector
from src.db_client import DBClient

logger = logging.getLogger(__name__)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Collect uptrend data from Finviz Elite")
    parser.add_argument("--db", default="data/uptrend.db", help="Database path")
    parser.add_argument("--worksheet", choices=VALID_WORKSHEETS, help="Collect specific worksheet only")
    parser.add_argument("--date", help="Date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch data without writing to DB")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    api_key = os.environ.get("FINVIZ_API_KEY")
    if not api_key:
        logger.error("FINVIZ_API_KEY environment variable is not set")
        sys.exit(1)

    config = CollectorConfig(finviz_api_key=api_key)
    db_client = DBClient(args.db)
    collector = DataCollector(db_client=db_client, config=config)

    if args.dry_run:
        # Fetch counts without writing to DB
        from src.constants import SECTORS
        worksheets = [args.worksheet] if args.worksheet else VALID_WORKSHEETS
        results = {}
        for ws in worksheets:
            try:
                sector = ws if ws != "all" else None
                count, total = collector._fetch_stock_count(sector)
                results[ws] = (count, total)
                logger.info("%s: count=%d, total=%d (dry run)", ws, count, total)
            except Exception as exc:
                logger.error("Failed to fetch %s: %s", ws, exc)
    elif args.worksheet:
        count, total = collector.collect_worksheet(args.worksheet, date=args.date)
        results = {args.worksheet: (count, total)}
    else:
        results = collector.collect_all(date=args.date)

    # Summary
    print("\nCollection Summary:")
    for ws, (count, total) in results.items():
        ratio = f"{count / total:.1%}" if total > 0 else "N/A"
        print(f"  {ws}: {count}/{total} ({ratio})")
    print(f"  Worksheets collected: {len(results)}")
    if args.dry_run:
        print("  (Dry run - no data written)")


if __name__ == "__main__":
    main()
