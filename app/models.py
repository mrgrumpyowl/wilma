#!/usr/bin/env python3

import os
import boto3
import botocore
from typing import List, Dict, Optional
from rich.console import Console
from halo import Halo

# Import the model_config module
from model_config import (
    MODEL_CONFIG,
    check_model_access,
    get_available_models,
    get_model_list,
    get_model_config,
)

console = Console(highlight=False)


def select_model(debug=False):
    """
    Present user with a list of available Anthropic models and handle selection.
    Only shows models that are both available in the current region and configured.
    """
    try:
        with Halo(
            text="Checking Anthropic models available to you in this region...",
            spinner="dots",
        ) as spinner:
            models = get_available_models(debug=debug)
            if not models:
                spinner.stop()
                console.print(
                    "[bold red]No Anthropic models are currently available in your region or you lack permissions to access them.[/]"
                )
                import sys

                sys.exit(1)
            spinner.stop()

        console.print("[bold blue]\nAvailable models:[/]")
        for idx, model in enumerate(models, 1):
            friendly_name = get_model_config(model)["friendly_name"]
            console.print(f"[bold blue]{idx}) {friendly_name}[/]")

        while True:
            try:
                choice = int(input("\nSelect a model (enter the number): "))
                if 1 <= choice <= len(models):
                    return models[choice - 1]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")
            except KeyboardInterrupt:
                print("\nInterrupted by user")
                try:
                    import sys

                    sys.exit(0)
                except SystemExit:
                    import os

                    os._exit(0)
    except Exception as e:
        console.print(f"[bold red]Error selecting model: {e}[/]")
        import sys

        sys.exit(1)


def check_default_model(default_model, region, debug=False):
    """
    Check if the default model is available and accessible.
    If not, fall back to model selection.
    """
    with Halo(text="Checking default model...", spinner="dots") as spinner:
        runtime_client = boto3.client("bedrock-runtime", region_name=region)
        if not get_model_config(default_model):
            spinner.stop()
            console.print(
                "[yellow]Default model not configured. Falling back to model selection...[/]"
            )
            return select_model(debug=debug)

        if check_model_access(runtime_client, default_model, debug):
            return default_model

        spinner.stop()
        console.print(
            "[yellow]Default model not available. Falling back to model selection...[/]"
        )
        return select_model(debug=debug)


def get_user_default_model():
    """
    Check for a user-defined default model in ~/.wilma/config.
    Returns the model name if found and valid, None otherwise.
    """
    config_path = os.path.expanduser("~/.wilma/config")

    # If config doesn't exist, silently return None
    if not os.path.exists(config_path):
        return None

    try:
        # Check if file is readable
        if not os.access(config_path, os.R_OK):
            console.print(
                "[yellow]Warning: ~/.wilma/config exists but is not readable[/]"
            )
            return None

        # Check file size
        if os.path.getsize(config_path) > 1024:  # Arbitrary 1KB limit
            console.print("[yellow]Warning: ~/.wilma/config is suspiciously large[/]")
            return None

        with open(config_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                if line.startswith("default_model"):
                    # Extract the model name between quotes
                    parts = line.split("=", 1)  # Split on first = only
                    if len(parts) != 2:
                        continue

                    model = parts[1].strip().strip("\"'")

                    # Validate model name format
                    if not model.startswith("anthropic."):
                        console.print(
                            "[yellow]Warning: Invalid model name format in ~/.wilma/config[/]"
                        )
                        return None

                    # Check for suspicious characters
                    if any(char in model for char in ";&|$<>{}[]\\"):
                        console.print(
                            "[yellow]Warning: Suspicious characters in model name in ~/.wilma/config[/]"
                        )
                        return None

                    # Optional: Check if this model exists in our known models
                    if not get_model_config(model):
                        console.print(
                            "[yellow]Warning: Unknown model specified in ~/.wilma/config[/]"
                        )
                        return None

                    return model

        return None

    except UnicodeDecodeError:
        console.print("[yellow]Warning: ~/.wilma/config is not a valid text file[/]")
        return None
    except Exception as e:
        if str(e):  # Only print if there's an actual error message
            console.print(
                f"[yellow]Warning: Error reading ~/.wilma/config: {str(e)}[/]"
            )
        return None


def get_model_details(model_id):
    """
    Get detailed information about a model.
    Returns a dictionary with model details.
    """
    model_config = get_model_config(model_id)
    if not model_config:
        return None

    # Add model_id to the config
    model_details = model_config.copy()
    model_details["model_id"] = model_id

    return model_details


def get_default_model_id():
    """
    Get the default model ID based on user preferences or system default.
    """
    # Check for user-defined default model
    user_default = get_user_default_model()

    # If user default exists, use it, otherwise use system default
    if user_default:
        return user_default
    else:
        return "anthropic.claude-3-7-sonnet-20250219-v1:0"  # System default
