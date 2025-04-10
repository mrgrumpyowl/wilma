#!/usr/bin/env python3

import sys
import os
from datetime import datetime
from rich.console import Console

# Import from refactored modules
from aws import check_aws_authentication, BedrockClient
from models import (
    select_model,
    check_default_model,
    get_user_default_model,
    get_model_details,
)
from chat import (
    ChatSession,
    ensure_chat_history_dir,
    get_todays_chat_dir,
    load_chat,
    select_chat_file,
    initialize_chat_session,
)
from ui import main_menu, show_welcome_message, show_error_message, show_success_message
from web_search import check_web_search_availability
from config import parse_arguments, get_app_config
from file_utils import detect_file_analysis_request
from model_config import get_model_config

console = Console(highlight=False)


def main():
    """Main entry point for the application."""
    # Check AWS authentication
    is_authenticated, region, error_message = check_aws_authentication()

    if not is_authenticated:
        show_error_message(f"AWS Authentication Error: {error_message}")
        sys.exit(1)

    show_success_message(f"Authenticated with AWS in region: {region}")

    # Parse command line arguments and get configuration
    args = parse_arguments()
    config = get_app_config()
    if config.get("bubble_mode", False):
        from ui import enable_bubble_mode

        enable_bubble_mode()

    # Check if web search is available
    web_search_enabled = check_web_search_availability(
        config.get("web_search_enabled", False)
    )

    # Model selection
    if config.get("show_model_menu", False):
        selected_model = select_model(debug=config.get("debug", False))
    else:
        # Check for user-defined default model
        user_default = get_user_default_model()
        default_model = user_default if user_default else config.get("default_model")
        selected_model = check_default_model(
            default_model, region, debug=config.get("debug", False)
        )

    # Get model details
    model_config = get_model_config(selected_model)
    if not model_config:
        show_error_message(f"Model configuration not found for {selected_model}")
        sys.exit(1)

    model_config["model_id"] = selected_model  # Add model_id to config

    # Initialize Bedrock client
    client = BedrockClient(
        region_name=region, max_retries=6, base_delay=1.0, max_delay=20.0
    )

    try:
        # Initialize chat history
        if args.ask or args.new:
            messages = []
        else:
            choice = main_menu()
            if choice == "2":
                chat_history_base_dir = ensure_chat_history_dir()
                chat_file = select_chat_file(chat_history_base_dir)
                if chat_file:
                    messages = load_chat(chat_file)
                else:
                    print("No chat selected or file not found.")
                    return
            else:
                messages = []

        # Initialize chat session
        session = initialize_chat_session(
            client=client,
            model_config=model_config,
            messages=messages,
            web_search_enabled=web_search_enabled,
        )

        if args.ask:
            # Process the ask argument and then start interactive session
            session.process_single_message(args.ask)
            # Start interactive session but skip the welcome message
            session.start_interactive_session(skip_welcome=True)
        else:
            # Normal interactive session with welcome message
            session.start_interactive_session()

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)


if __name__ == "__main__":
    main()
