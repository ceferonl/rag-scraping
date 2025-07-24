"""
Configuration management for RAG Scraping.

This module handles loading and managing configuration from YAML files,
with support for different run types (demo vs main).
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables from .env automatically
load_dotenv()


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def get_output_paths(config: Dict[str, Any], run_type: str = None) -> Dict[str, Path]:
    """
    Get output paths for a specific run type.

    Args:
        config: Configuration dictionary
        run_type: Run type ("demo" or "production"). If None, uses default from config.

    Returns:
        Dictionary of output paths
    """
    if run_type is None:
        run_type = config['output']['default_run_type']

    if run_type not in ['demo', 'production']:
        raise ValueError(f"Invalid run_type: {run_type}. Must be 'demo' or 'production'")

    # Get base directory for this run type
    base_dir_key = f"{run_type}_base_dir"
    base_dir = Path(config['output'][base_dir_key])

    # Create subdirectories relative to base directory
    pdfs_dir = base_dir / config['output']['pdfs_subdir']
    images_dir = base_dir / config['output']['images_subdir']

    # Ensure directories exist
    base_dir.mkdir(parents=True, exist_ok=True)
    pdfs_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    return {
        'base_dir': base_dir,
        'pdfs_dir': pdfs_dir,
        'images_dir': images_dir,
        'run_type': run_type
    }


def get_timestamp(config: Dict[str, Any]) -> str:
    """
    Get current timestamp in configured format.

    Args:
        config: Configuration dictionary

    Returns:
        Formatted timestamp string
    """
    format_str = config['output']['timestamp_format']
    return datetime.now().strftime(format_str)


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate configuration structure.

    Args:
        config: Configuration dictionary

    Raises:
        ValueError: If configuration is invalid
    """
    required_sections = ['scraping', 'pdf', 'output', 'rag', 'logging']

    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required configuration section: {section}")

    # Validate output configuration
    output_config = config['output']
    required_output_keys = ['demo_base_dir', 'production_base_dir', 'pdfs_subdir', 'images_subdir']

    for key in required_output_keys:
        if key not in output_config:
            raise ValueError(f"Missing required output configuration key: {key}")

    # Validate run type
    default_run_type = output_config.get('default_run_type', 'demo')
    if default_run_type not in ['demo', 'production']:
        raise ValueError(f"Invalid default_run_type: {default_run_type}. Must be 'demo' or 'production'")


# Convenience function for common configuration loading
def load_config_with_paths(config_path: str = "config.yaml", run_type: str = None) -> Dict[str, Any]:
    """
    Load configuration and get output paths in one call.

    Args:
        config_path: Path to configuration file
        run_type: Run type ("demo" or "main")

    Returns:
        Configuration dictionary with output paths added
    """
    config = load_config(config_path)
    validate_config(config)

    # Add output paths to config
    config['output_paths'] = get_output_paths(config, run_type)
    config['timestamp'] = get_timestamp(config)

    return config
