"""
APEX INDIA — Configuration Loader
====================================
Loads config.yaml with environment variable interpolation,
validation, and safe access patterns.

Usage:
    from apex_india.utils.config import config
    broker_key = config.get("broker.zerodha.api_key")
    risk_limit = config.get("risk.position.max_risk_per_trade_pct")
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

from apex_india.utils.logger import get_logger

logger = get_logger("utils.config")


# ═══════════════════════════════════════════════════════════════
# ENVIRONMENT VARIABLE INTERPOLATION
# ═══════════════════════════════════════════════════════════════

_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def _interpolate_env_vars(value: Any) -> Any:
    """
    Recursively resolve ${ENV_VAR} references in config values.
    Returns the original value if no env var is found or if the
    env var is not set (preserves the placeholder for debugging).
    """
    if isinstance(value, str):
        def _replace(match):
            env_name = match.group(1)
            env_value = os.environ.get(env_name)
            if env_value is None:
                logger.warning(
                    f"Environment variable '{env_name}' not set — "
                    f"using placeholder"
                )
                return match.group(0)  # Keep ${VAR} as-is
            return env_value
        return _ENV_VAR_PATTERN.sub(_replace, value)
    elif isinstance(value, dict):
        return {k: _interpolate_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_interpolate_env_vars(item) for item in value]
    return value


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION CLASS
# ═══════════════════════════════════════════════════════════════

class Config:
    """
    Centralized configuration manager.

    Loads config.yaml, interpolates environment variables,
    and provides dot-notation access to nested keys.

    Example:
        config = Config()
        config.get("risk.position.max_risk_per_trade_pct")  # → 0.01
        config.get("broker.primary")                         # → "zerodha"
        config.get("nonexistent.key", default=42)            # → 42
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration from YAML file.

        Args:
            config_path: Path to config.yaml. If None, searches for:
                         1. APEX_CONFIG_PATH env var
                         2. config.yaml in project root
        """
        # Load .env file if present
        project_root = Path(__file__).resolve().parent.parent.parent
        env_file = project_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            logger.info(f"Loaded environment variables from {env_file}")

        # Resolve config file path
        if config_path:
            self._config_path = Path(config_path)
        elif os.environ.get("APEX_CONFIG_PATH"):
            self._config_path = Path(os.environ["APEX_CONFIG_PATH"])
        else:
            self._config_path = project_root / "config.yaml"

        # Load and parse
        self._raw_data: Dict[str, Any] = {}
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load and parse the YAML configuration file."""
        if not self._config_path.exists():
            logger.error(f"Configuration file not found: {self._config_path}")
            raise FileNotFoundError(
                f"Configuration file not found: {self._config_path}"
            )

        with open(self._config_path, "r", encoding="utf-8") as f:
            self._raw_data = yaml.safe_load(f) or {}

        # Interpolate environment variables
        self._data = _interpolate_env_vars(self._raw_data)

        logger.info(
            f"Configuration loaded from {self._config_path} "
            f"({len(self._raw_data)} top-level keys)"
        )

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot-notation path.

        Args:
            key_path: Dot-separated path, e.g. "risk.position.max_risk_per_trade_pct"
            default: Value to return if key not found

        Returns:
            The configuration value, or default if not found.
        """
        keys = key_path.split(".")
        current = self._data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        return current

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section as a dictionary.

        Args:
            section: Top-level section name, e.g. "risk", "broker"

        Returns:
            Dictionary of the section, or empty dict if not found.
        """
        return self._data.get(section, {})

    @property
    def mode(self) -> str:
        """Get the current system operating mode (paper/live/backtest)."""
        return self.get("system.mode", "paper")

    @property
    def is_live(self) -> bool:
        """Check if system is in live trading mode."""
        return self.mode == "live"

    @property
    def is_paper(self) -> bool:
        """Check if system is in paper trading mode."""
        return self.mode == "paper"

    @property
    def is_backtest(self) -> bool:
        """Check if system is in backtesting mode."""
        return self.mode == "backtest"

    @property
    def log_level(self) -> str:
        """Get the configured log level."""
        return self.get("system.log_level", "INFO")

    @property
    def primary_broker(self) -> str:
        """Get the primary broker name."""
        return self.get("broker.primary", "zerodha")

    def reload(self) -> None:
        """Reload configuration from disk (useful for hot-reloading)."""
        logger.info("Reloading configuration...")
        self._load()

    def validate(self) -> bool:
        """
        Validate critical configuration values exist and are sensible.
        Returns True if valid, raises ValueError otherwise.
        """
        errors = []

        # System mode must be valid
        if self.mode not in ("paper", "live", "backtest"):
            errors.append(
                f"Invalid system.mode: '{self.mode}' — "
                f"must be 'paper', 'live', or 'backtest'"
            )

        # Risk limits must be positive and sensible
        max_risk = self.get("risk.position.max_risk_per_trade_pct")
        if max_risk is not None and (max_risk <= 0 or max_risk > 0.05):
            errors.append(
                f"risk.position.max_risk_per_trade_pct={max_risk} — "
                f"must be between 0 and 0.05 (5%)"
            )

        # Min risk-reward must be > 1
        min_rr = self.get("risk.position.min_risk_reward")
        if min_rr is not None and min_rr < 1.0:
            errors.append(
                f"risk.position.min_risk_reward={min_rr} — must be ≥ 1.0"
            )

        # Drawdown limit must be reasonable
        max_dd = self.get("risk.circuit_breakers.max_drawdown_pct")
        if max_dd is not None and (max_dd <= 0 or max_dd > 0.30):
            errors.append(
                f"risk.circuit_breakers.max_drawdown_pct={max_dd} — "
                f"must be between 0 and 0.30 (30%)"
            )

        if errors:
            for err in errors:
                logger.error(f"Config validation failed: {err}")
            raise ValueError(
                f"Configuration validation failed with {len(errors)} error(s):\n"
                + "\n".join(f"  • {e}" for e in errors)
            )

        logger.info("Configuration validation passed ✓")
        return True

    def __repr__(self) -> str:
        return (
            f"Config(path={self._config_path}, mode={self.mode}, "
            f"broker={self.primary_broker})"
        )


# ═══════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════

# Global config instance — lazy-loaded on first access
_config_instance: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get the global Config singleton.
    Creates the instance on first call, reuses on subsequent calls.

    Args:
        config_path: Optional path to config.yaml (only used on first call)

    Returns:
        The global Config instance.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


# Convenience alias
config = property(lambda self: get_config())
