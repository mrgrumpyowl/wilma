#!/usr/bin/env python3

import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from rich import print
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.rule import Rule
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML
from code_blocks import handle_copy_command

# Import from other modules in the refactored structure
from aws import (
    BedrockClient,
    TokenExpiredException,
    InferenceProfileRequired,
    refresh_aws_session,
)
from ui import display_message, is_bubble_mode_enabled, format_message_as_bubble

console = Console(highlight=False)
current_chat_file = None


def ensure_chat_history_dir():
    """Ensures that the chat history base directory exists."""
    home_dir = os.path.expanduser("~")
    chat_history_base_dir = os.path.join(
        home_dir, ".wilma", "chat-history", "anthropic"
    )
    os.makedirs(chat_history_base_dir, exist_ok=True)
    return chat_history_base_dir


def get_todays_chat_dir(chat_history_base_dir):
    """Returns today's chat directory, creating it if necessary."""
    today = datetime.now().strftime("%Y-%m-%d")
    todays_chat_dir = os.path.join(chat_history_base_dir, today)
    os.makedirs(todays_chat_dir, exist_ok=True)
    return todays_chat_dir


def save_chat(chat_data, chat_dir):
    """Saves current chat data to the session file."""
    global current_chat_file
    if not current_chat_file:
        time_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{time_stamp}.json"
        current_chat_file = os.path.join(chat_dir, filename)

    with open(current_chat_file, "w", encoding="utf-8") as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=4)


def load_chat(file_path):
    """Loads chat data from a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def select_chat_file(chat_history_base_dir):
    """Provides a UI to select an old chat file from available files."""
    files = []
    for subdir, dirs, files_in_dir in os.walk(chat_history_base_dir):
        for file in files_in_dir:
            if file.endswith(".json"):
                full_path = os.path.join(subdir, file)
                files.append(full_path)
    files = sorted(files, reverse=True)[:20]

    if not files:
        print("No previous chats available.")
        return None
        console.print(
            "[bold cyan]\nYour 20 most recent chats, sorted by most recent first:[/]"
        )
    for idx, file in enumerate(files):
        display_name = os.path.splitext(os.path.basename(file))[0]
        print(f"{idx + 1}) {display_name}")

    print(
        "\nSelect a file to resume (number), or press Enter for the most recent chat: "
    )
    user_input = input().strip()
    if user_input == "":
        return files[0]

    try:
        choice = int(user_input) - 1
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None

    if 0 <= choice < len(files):
        return files[choice]
    else:
        print("Invalid choice. Please select a valid file number.")
        return None


def should_exit(content: str) -> bool:
    """Check if the user wants to exit the chat."""
    return content.lower() == "exit"


def append_message(messages: list, role: str, content: str):
    """Append a message to the chat history."""
    messages.append({"role": role, "content": content})


class ChatSession:
    """Manages a chat session with a model."""

    def __init__(
        self, client, model_config, messages, system_prompt, web_search_enabled=False
    ):
        self.client = client
        self.model_config = model_config
        self.messages = messages
        self.system_prompt = system_prompt
        self.web_search_enabled = web_search_enabled
        self.selected_model = model_config["model_id"]
        self.supports_streaming = model_config.get("supports_streaming", True)

    def process_message(self, content):
        """Process a single message and get the model's response"""
        # Import here to avoid circular imports
        from file_utils import (
            detect_file_analysis_request,
            generate_markdown_from_directory,
            read_file_contents,
            estimate_token_count,
        )
        from web_search import should_perform_web_search, perform_web_search
        from ui import get_user_input

        if handle_copy_command(content):                                                                                                                                                                                                                       
            return True

        if should_exit(content):
            return False

        # Display user message in bubble format if enabled
        if is_bubble_mode_enabled():
            display_message(content, is_user=True)
        is_file_request, path, is_directory = detect_file_analysis_request(content)
        if is_file_request:
            if is_directory:
                markdown_content, token_count = generate_markdown_from_directory(path)
                if markdown_content == "DIRECTORY TOO BIG.":
                    console.print(
                        f"[yellow]\nThe directory is too large to upload because it is likely larger than 100,000 tokens.\n"
                        f"Estimated token count for this recursive directory analysis:[/] {token_count}\n"
                    )
                if markdown_content:
                    dir_analysis_request = (
                        f"The following describes a directory structure along with all its contents in "
                        f"Markdown format. "
                        f"Please carefully analyse the directory structure and the files contained within. Pay "
                        f"attention to whether the directory structure looks like a code repository. Then take a "
                        f"deep breath and provide a brief summary of your analysis. End your response with an "
                        f"assurance that you have memorised the contents of the repository and you are ready to "
                        f"answer the user's questions.\n\n{markdown_content}"
                    )
                    append_message(self.messages, "user", dir_analysis_request)
                    console.print(
                        f"[yellow]\nEstimated token count for this recursive directory analysis:[/] {token_count}\n"
                    )
                else:
                    print_formatted_text(
                        HTML(
                            "<ansired>Directory is empty or contains no readable files.</ansired>"
                        )
                    )
                    return True
            else:
                file_name, file_contents, token_count = read_file_contents(path)
                if file_contents == "FILE TOO BIG.":
                    console.print(
                        f"[yellow]\nThe file: {file_name} is too large to upload because it is likely larger than 64,000 tokens.\n"
                        f"Estimated token count for this file:[/] {token_count}\n"
                    )
                elif file_contents:
                    file_analysis_request = (
                        f"Please analyse the contents of the following file:\n"
                        f"\n{file_name}\n"
                        f"\n{file_contents}\n"
                        f"\nEnd your response by asking the user what questions they have about the file."
                    )
                    append_message(self.messages, "user", file_analysis_request)
                    console.print(
                        f"[yellow]\nEstimated token count for this file:[/] {token_count}\n"
                    )
                else:
                    print_formatted_text(HTML(f"\nThe file: {file_name} is empty.\n"))
                    console.print(
                        f"[yellow]Estimated token count for this file:[/] {token_count}\n"
                    )
                    return True
        else:
            append_message(self.messages, "user", content)

            if self.web_search_enabled:
                web_search_needed, search_query = should_perform_web_search(
                    content, self.selected_model, self.model_config, self.client
                )

                response_content = ""
                if web_search_needed:
                    console.print(f"[yellow]Web search in progress...\n[/]")
                    try:
                        web_search_results = perform_web_search(search_query)
                        response_content += f"<web-search-results> {web_search_results} </web-search-results>"
                    except Exception as e:
                        print(f"Error during web search: {e}")

                if response_content:
                    append_message(self.messages, "assistant", response_content)
                    websearch_analysis_request = (
                        "Thank you for carrying out a web search on my behalf with Perplexity. "
                        "The results of the Perplexity web search are contained in the <web-search-results> XML tag in your previous assistant content. "
                        "You will now take ownership of those <web-search-results> and present them to me, the user, as your own 'research'. "
                        "Now reflect on those <web-search-results> to augment and inform your own training data as you carefully provide an "
                        "excellent answer to my original query. Keep these <web-search-results> in mind as we continue our conversation."
                    )

                    append_message(self.messages, "user", websearch_analysis_request)

        while True:  # Token refresh retry loop
            try:
                complete_message = ""

                if self.supports_streaming:
                    stream = self.client.create_message(
                        model_id=self.selected_model,
                        messages=self.messages,
                        system=self.system_prompt,
                        max_tokens=self.model_config["max_tokens"],
                        temperature=self.model_config["temperature"],
                        stream=True,
                    )
                    if is_bubble_mode_enabled():
                        # For bubble mode, collect the entire message first
                        complete_message = ""
                        with console.status(
                            "[bold green]Thinking...", spinner="dots"
                        ) as status:
                            for chunk in stream:
                                if chunk.type == "content_block_delta":
                                    if chunk.delta.text:
                                        complete_message += chunk.delta.text
                                elif chunk.type == "message_stop":
                                    break
                        display_message(
                            complete_message,
                            is_user=False,
                            model_name=self.model_config["friendly_name"],
                        )
                    else:
                        # Original streaming display for non-bubble mode
                        # Use Live display to show streaming response
                        with Live(
                            Markdown(complete_message),
                            refresh_per_second=10,
                            console=console,
                            transient=False,
                        ) as live:
                            for chunk in stream:
                                if chunk.type == "content_block_delta":
                                    if chunk.delta.text:
                                        complete_message += chunk.delta.text
                                        live.update(Markdown(complete_message))
                                elif chunk.type == "message_stop":
                                    break
                        # After streaming completes                                                                                                                                                                                                                                
                        from code_blocks import process_markdown_for_code_blocks, get_copy_help_text                                                                                                                                                                               
                                                                                                                                                                                                                                                                                
                        # Process the complete message for code blocks                                                                                                                                                                                                             
                        processed_message = process_markdown_for_code_blocks(complete_message)                                                                                                                                                                                     
                        console.print(Markdown(processed_message))                                                                                                                                                                                                                 
                                                                                                                                                                                                                                                                                
                        # Display help text for copying                                                                                                                                                                                                                            
                        help_text = get_copy_help_text()                                                                                                                                                                                                                           
                        if help_text:                                                                                                                                                                                                                                              
                            console.print(help_text) 
                else:
                    # For non-streaming responses
                    response = self.client.create_message(
                        model_id=self.selected_model,
                        messages=self.messages,
                        system=self.system_prompt,
                        max_tokens=self.model_config["max_tokens"],
                        temperature=self.model_config["temperature"],
                    )
                    complete_message = response.content[0].text

                    # Display the message since it wasn't streamed
                    if is_bubble_mode_enabled():
                        display_message(
                            complete_message,
                            is_user=False,
                            model_name=self.model_config["friendly_name"],
                        )
                    else:
                        console.print(Markdown(complete_message))

                append_message(self.messages, "assistant", complete_message)
                print("\n")
                print(Rule(), "")

                # Save chat after successful response
                chat_history_base_dir = ensure_chat_history_dir()
                todays_chat_dir = get_todays_chat_dir(chat_history_base_dir)
                save_chat(self.messages, todays_chat_dir)

                break  # Break out of token refresh retry loop on success

            except (TokenExpiredException, InferenceProfileRequired) as e:
                console.print(f"[yellow]\n{str(e)}[/]")
                if isinstance(e, TokenExpiredException):
                    console.print(
                        f"[yellow]Please reauthenticate using your preferred method (e.g. Leapp or saml2aws)[/]"
                    )
                else:
                    console.print(
                        f"[yellow]Please create an inference profile for this model in AWS Bedrock console.[/]"
                    )

                while True:  # Token refresh prompt loop
                    try:
                        input(
                            "\nPress ENTER to retry after addressing the issue, or CTRL+C to exit..."
                        )

                        # Force refresh of AWS credentials
                        success, new_region, error_msg = refresh_aws_session()
                        if not success:
                            console.print(
                                f"[yellow]\n{error_msg}\nPlease ensure you have addressed the issue properly.[/]"
                            )
                            continue

                        # Create new client with fresh credentials
                        self.client = BedrockClient(
                            region_name=new_region,
                            max_retries=6,
                            base_delay=1.0,
                            max_delay=20.0,
                        )

                        # Verify the new client works
                        from aws import check_aws_authentication

                        is_authenticated, _, auth_error = check_aws_authentication()
                        if not is_authenticated:
                            if auth_error:
                                console.print(f"[yellow]\n{auth_error}[/]")
                            console.print(
                                "[yellow]\nFailed to establish connection with AWS. Please try again.[/]"
                            )
                            continue

                        console.print(
                            f"[yellow]\nSuccessfully reconnected. Retrying your request...\n[/]"
                        )
                        break  # Break out of token refresh prompt loop

                    except KeyboardInterrupt:
                        print("\nExiting...")
        return True

    def process_single_message(self, content):
        """Process a single message and return, without starting an interactive session"""
        self.process_message(content)

    def start_interactive_session(self, skip_welcome=False):
        """Start the interactive chat session loop"""
        # Import here to avoid circular imports
        from ui import get_user_input

        try:
            if not skip_welcome:
                welcome = f"""                                                                                                                                                                                                                             
You're now chatting with {self.model_config['friendly_name']} via Amazon Bedrock.                                                                                                                                                                          
The user prompt handles multiline input, so Enter gives a newline.                                                                                                                                                                                         
To submit your prompt hit Esc -> Enter.                                                                                                                                                                                                                    
To exit gracefully simply submit the word: "exit", or hit Ctrl+C.                                                                                                                                                                                          
                                                                                                                                                                                                                                                        
You can pass individual utf-8 encoded files by entering "Upload: ~/path/to/file_name"                                                                                                                                                                      
You can pass entire directories (recursively) by entering "Upload: ~/path/to/directory"                                                                                                                                                                    
"""
                console.print(f"[bold blue]{welcome}[/]")

            while True:
                content = get_user_input()
                if not self.process_message(content):
                    break

        except KeyboardInterrupt:
            print("\nInterrupted by user")
            try:
                sys.exit(0)
            except SystemExit:
                os._exit(0)


def create_system_prompt(model_config):
    """Create a system prompt based on model configuration and current time."""
    friendly_name = model_config["friendly_name"]
    training_cutoff = model_config["training_cutoff"]

    # Set up system prompt with current date and time
    now = datetime.now()
    local_date = now.strftime("%a %d %b %Y")
    local_time = now.strftime("%H:%M:%S %Z")

    system_prompt = (
        f'Specifically, your model is "{friendly_name}". Your knowledge base was last updated '
        f"in {training_cutoff}. Today is {local_date}. Local time is {local_time}. You write in British "
        f"English and you are not too quick to apologise or thank the user. You MUST format your "
        f"responses in Markdown syntax. Use `- ` for any unnumbered bullet point lists, as per "
        f"standard Markdown syntax."
    )

    return system_prompt


def initialize_chat_session(
    client, model_config, messages=None, web_search_enabled=False
):
    """Initialize a new chat session with the given model configuration."""
    if messages is None:
        messages = []

    system_prompt = create_system_prompt(model_config)

    return ChatSession(
        client=client,
        model_config=model_config,
        messages=messages,
        system_prompt=system_prompt,
        web_search_enabled=web_search_enabled,
    )
