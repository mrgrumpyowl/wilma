#!/usr/bin/env python3

import argparse
import os
from typing import Dict, Any, Optional
from rich.console import Console

console = Console(highlight=False)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Universal Chatbot - Chat with Anthropic's Claude models "
            "\nUse your own Anthropic API key to chat with their latest LLMs."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-a",
        "--ask",
        type=str,
        metavar="PROMPT",
        help="Quick-start a new chat with an initial question/prompt.",
    )
    parser.add_argument(
        "-m",
        "--model-select",
        nargs="?",
        const="show_menu",
        metavar="MODEL",
        help="Select the Anthropic (via Amazon Bedrock) model to use. Options:\n"
        "  - Specify a model name directly\n"
        "  - Use without a value to select from a list of models available in your authenticated AWS region\n"
        "  - Omit to use the default model (claude-3-7-sonnet-20250219-v1:0)\n",
    )
    parser.add_argument(
        "-ws",
        "--web-search",
        action="store_true",
        help="Enable web search functionality for answering queries.",
    )
    parser.add_argument(
        "-1",
        "--new",
        action="store_true",
        help="Quick-start a new chat skipping the first menu.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument(
        "--bubble", action="store_true", help="Enable modern chat bubble UI mode."
    )
    return parser.parse_args()


def get_config_path() -> str:
    """Get the path to the config file."""
    return os.path.expanduser("~/.wilma/config")


def ensure_config_dir():
    """Ensure the config directory exists."""
    config_dir = os.path.dirname(get_config_path())
    os.makedirs(config_dir, exist_ok=True)


def read_config_file() -> Dict[str, str]:
    """
    Read configuration from the config file.
    Returns a dictionary of configuration values.
    """
    config = {}
    config_path = get_config_path()

    if not os.path.exists(config_path):
        return config

    try:
        # Check if file is readable
        if not os.access(config_path, os.R_OK):
            console.print(
                "[yellow]Warning: ~/.wilma/config exists but is not readable[/]"
            )
            return config

        # Check file size
        if os.path.getsize(config_path) > 1024:  # Arbitrary 1KB limit
            console.print("[yellow]Warning: ~/.wilma/config is suspiciously large[/]")
            return config

        with open(config_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse key=value pairs
                if "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip().strip("\"'")

    except UnicodeDecodeError:
        console.print("[yellow]Warning: ~/.wilma/config is not a valid text file[/]")
    except Exception as e:
        if str(e):  # Only print if there's an actual error message
            console.print(
                f"[yellow]Warning: Error reading ~/.wilma/config: {str(e)}[/]"
            )

    return config


def write_config_value(key: str, value: str):
    """
    Write a configuration value to the config file.
    If the key already exists, it will be updated.
    """
    ensure_config_dir()
    config_path = get_config_path()
    config = read_config_file()

    # Update the value
    config[key] = value

    # Write the updated config
    try:
        with open(config_path, "w") as f:
            for k, v in config.items():
                f.write(f"{k}={v}\n")
        return True
    except Exception as e:
        console.print(f"[red]Error writing to config file: {str(e)}[/]")
        return False


def get_config_value(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a configuration value from the config file.
    Returns the value if found, otherwise returns the default.
    """
    config = read_config_file()
    return config.get(key, default)


def get_app_config() -> Dict[str, Any]:
    """
    Get the complete application configuration by combining:
    - Default values
    - Config file values
    - Environment variables
    - Command line arguments

    Returns a dictionary with the complete configuration.
    """
    # Start with default values
    config = {
        "default_model": "anthropic.claude-3-7-sonnet-20250219-v1:0",
        "web_search_enabled": False,
        "debug": False,
    }

    # Update with config file values
    file_config = read_config_file()
    if "default_model" in file_config:
        config["default_model"] = file_config["default_model"]
    if "inference_profile" in file_config:
        config["inference_profile"] = file_config["inference_profile"]

    # Update with environment variables
    if os.getenv("WILMA_DEFAULT_MODEL"):
        config["default_model"] = os.getenv("WILMA_DEFAULT_MODEL")
    if os.getenv("WILMA_DEBUG") in ("1", "true", "yes", "y"):
        config["debug"] = True
    if os.getenv("PERPLEXITY_API_KEY"):
        config["perplexity_api_key"] = os.getenv("PERPLEXITY_API_KEY")

    # Update with command line arguments
    args = parse_arguments()
    if args.model_select and args.model_select != "show_menu":
        config["default_model"] = args.model_select
    if args.model_select == "show_menu":
        config["show_model_menu"] = True
    if args.web_search:
        config["web_search_enabled"] = True
    if args.debug:
        config["debug"] = True
    if args.ask:
        config["initial_prompt"] = args.ask
    if args.new:
        config["skip_menu"] = True
    if args.bubble:
        config["bubble_mode"] = True

    return config
