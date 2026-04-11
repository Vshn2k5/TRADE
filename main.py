"""
APEX INDIA -- System Entry Point
==================================
Main entry point for the Autonomous Quantitative Trading System.
Provides CLI commands for starting, stopping, and monitoring
the system in different modes.

Usage:
    python main.py --status              # Check system status
    python main.py --mode paper          # Start in paper trading mode
    python main.py --mode backtest       # Run backtesting engine
    python main.py --init-db             # Initialize database tables
    python main.py --validate-config     # Validate configuration
"""

import sys
import os
import io
import argparse
from datetime import datetime
from pathlib import Path

# Force UTF-8 stdout on Windows to handle special characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure project root is in Python path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def print_banner():
    """Print the APEX INDIA startup banner."""
    banner = """
    +===============================================================+
    |                                                               |
    |          A P E X   I N D I A   v 3 . 0                       |
    |                                                               |
    |        Autonomous Quantitative Trading Intelligence           |
    |        BSE Sensex - Nifty 50 - F&O - MCX                     |
    |                                                               |
    |   "The market rewards patience, punishes greed,              |
    |    and destroys those without a plan."                        |
    |                                                               |
    +===============================================================+
    """
    print(banner)


def cmd_status():
    """Display full system status."""
    from apex_india.utils.config import get_config
    from apex_india.utils.logger import get_logger
    from apex_india.data.storage.database import get_database
    from scheduler import MarketCalendar

    logger = get_logger("main")
    print_banner()

    # Configuration
    print("\n" + "=" * 60)
    print("  SYSTEM CONFIGURATION")
    print("=" * 60)

    try:
        config = get_config()
        print(f"  Config File      : {config._config_path}")
        print(f"  System Mode      : {config.mode.upper()}")
        print(f"  Primary Broker   : {config.primary_broker}")
        print(f"  Log Level        : {config.log_level}")
        print(f"  Config Valid     : ", end="")
        try:
            config.validate()
            print("✓ PASSED")
        except ValueError as e:
            print(f"✗ FAILED — {e}")
    except Exception as e:
        print(f"  ✗ Config load failed: {e}")

    # Market Calendar
    print("\n" + "-" * 60)
    print("  MARKET STATUS")
    print("-" * 60)
    calendar = MarketCalendar()
    now = datetime.now(calendar.IST)

    print(f"  Current Time     : {now.strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"  Trading Day      : {'Yes ✓' if calendar.is_trading_day() else 'No ✗'}")
    print(f"  Market Open      : {'Yes ✓' if calendar.is_market_open() else 'No ✗'}")
    print(f"  Session          : {calendar.current_session()}")
    print(f"  Next Market Open : {calendar.next_market_open().strftime('%Y-%m-%d %H:%M IST')}")

    # Database
    print("\n" + "-" * 60)
    print("  DATABASE STATUS")
    print("-" * 60)
    try:
        db = get_database()
        health = db.health_check()
        for service, status in health.items():
            icon = "✓" if status in ("connected",) else "⚠" if "disabled" in str(status) else "✗"
            print(f"  {service:18s}: {icon} {status}")
    except Exception as e:
        print(f"  ✗ Database check failed: {e}")

    # Package versions
    print("\n" + "-" * 60)
    print("  KEY DEPENDENCIES")
    print("-" * 60)

    packages = [
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("sqlalchemy", "sqlalchemy"),
        ("loguru", "loguru"),
        ("yaml", "yaml"),
    ]

    for display_name, import_name in packages:
        try:
            mod = __import__(import_name)
            version = getattr(mod, "__version__", "installed")
            print(f"  {display_name:18s}: ✓ {version}")
        except ImportError:
            print(f"  {display_name:18s}: ✗ NOT INSTALLED")

    # Optional heavy packages
    optional = [
        ("scikit-learn", "sklearn"),
        ("lightgbm", "lightgbm"),
        ("torch", "torch"),
        ("streamlit", "streamlit"),
        ("kiteconnect", "kiteconnect"),
        ("redis", "redis"),
        ("APScheduler", "apscheduler"),
    ]

    print("\n  Optional:")
    for display_name, import_name in optional:
        try:
            mod = __import__(import_name)
            version = getattr(mod, "__version__", "installed")
            print(f"  {display_name:18s}: ✓ {version}")
        except ImportError:
            print(f"  {display_name:18s}: ○ not installed")

    print("\n" + "=" * 60)
    print("  System status check complete.")
    print("=" * 60 + "\n")


def cmd_init_db():
    """Initialize database tables."""
    from apex_india.utils.logger import get_logger
    from apex_india.data.storage.database import get_database

    logger = get_logger("main")
    print_banner()

    print("\nInitializing database tables...")
    db = get_database()
    db.create_tables()
    print("Database tables created successfully ✓")

    health = db.health_check()
    print(f"Database backend: {health.get('sql_backend', 'unknown')}")
    print(f"Connection status: {health.get('sql_database', 'unknown')}")


def cmd_validate_config():
    """Validate the configuration file."""
    from apex_india.utils.config import get_config

    print_banner()
    print("\nValidating configuration...")

    try:
        config = get_config()
        config.validate()
        print("Configuration validation PASSED ✓")
        print(f"  Mode: {config.mode}")
        print(f"  Broker: {config.primary_broker}")
        print(f"  Risk per trade: {config.get('risk.position.max_risk_per_trade_pct')}")
        print(f"  Max drawdown: {config.get('risk.circuit_breakers.max_drawdown_pct')}")
        print(f"  Strategies enabled: {len(config.get('strategies.enabled', []))}")
    except Exception as e:
        print(f"Configuration validation FAILED ✗")
        print(f"  Error: {e}")
        sys.exit(1)


def cmd_start(mode: str):
    """Start the APEX INDIA trading system."""
    from apex_india.utils.config import get_config
    from apex_india.utils.logger import get_logger, reconfigure
    from apex_india.data.storage.database import get_database
    from scheduler import ApexScheduler

    print_banner()

    config = get_config()
    reconfigure(config.log_level)
    logger = get_logger("main")

    # Override mode if specified via CLI
    if mode:
        logger.info(f"Mode override from CLI: {mode}")

    effective_mode = mode or config.mode

    logger.info(f"Starting APEX INDIA v3.0 in {effective_mode.upper()} mode...")

    # Safety check for live mode
    if effective_mode == "live":
        print("\n" + "!" * 60)
        print("  ⚠️  WARNING: LIVE TRADING MODE")
        print("  This will execute REAL trades with REAL money.")
        print("!" * 60)
        confirm = input("\n  Type 'CONFIRM LIVE' to proceed: ")
        if confirm.strip() != "CONFIRM LIVE":
            print("  Live mode aborted. Use --mode paper for safety.")
            sys.exit(0)

    # Initialize database
    logger.info("Initializing database...")
    db = get_database()
    db.create_tables()

    # Health check
    health = db.health_check()
    logger.info(f"Database health: {health}")

    # Initialize scheduler
    scheduler = ApexScheduler()

    # Register placeholder tasks (will be replaced with real implementations)
    def heartbeat():
        logger.debug("Heartbeat: System alive")

    scheduler.register_task(
        "heartbeat",
        heartbeat,
        trigger="interval",
        seconds=300,  # Every 5 minutes
        market_hours_only=False,
    )

    # TODO: Register real tasks in Phase 2+:
    # scheduler.register_task("data_ingest", data_pipeline.run, seconds=60)
    # scheduler.register_task("signal_compute", signal_engine.run, seconds=60)
    # scheduler.register_task("position_monitor", pos_monitor.run, seconds=60)
    # scheduler.register_task("regime_check", regime_detector.run, minutes=15)

    # Start
    scheduler.start()

    status = scheduler.get_status()
    logger.info(f"Scheduler status: {status}")

    logger.info(
        f"APEX INDIA is running in {effective_mode.upper()} mode. "
        f"Press Ctrl+C to stop."
    )

    # Block until shutdown
    scheduler.run_forever()

    # Cleanup
    logger.info("Shutting down APEX INDIA...")
    db.close()
    logger.info("APEX INDIA shutdown complete. Goodbye.")


def main():
    """Parse CLI arguments and dispatch commands."""
    parser = argparse.ArgumentParser(
        description="APEX INDIA — Autonomous Quantitative Trading System v3.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --status              Show system status
  python main.py --mode paper          Start paper trading
  python main.py --mode live           Start live trading (requires confirmation)
  python main.py --init-db             Initialize database tables
  python main.py --validate-config     Validate configuration file
        """,
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Display system status and health check",
    )
    parser.add_argument(
        "--mode",
        choices=["paper", "live", "backtest"],
        help="Operating mode: paper (simulated), live (real), backtest",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database tables",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate the configuration file",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config.yaml (default: ./config.yaml)",
    )

    args = parser.parse_args()

    # Set config path if provided
    if args.config:
        os.environ["APEX_CONFIG_PATH"] = args.config

    # Dispatch commands
    if args.status:
        cmd_status()
    elif args.init_db:
        cmd_init_db()
    elif args.validate_config:
        cmd_validate_config()
    elif args.mode:
        cmd_start(args.mode)
    else:
        # Default: show status
        cmd_status()


if __name__ == "__main__":
    main()
