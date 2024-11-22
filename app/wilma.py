#!/usr/bin/env python3

import argparse
import boto3
import botocore
import fnmatch
import json
import os
import random
import requests
import sys
import subprocess
import tiktoken
import time

from datetime import datetime
from halo import Halo
from prompt_toolkit import prompt
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML
from rich import print
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.rule import Rule
from typing import Optional, Tuple

from model_config import check_model_access, get_available_models, get_model_list, get_model_config

console = Console(highlight=False)
current_chat_file = None

def check_aws_authentication() -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check if the user has an active AWS session and get their region.
    Returns a tuple of (is_authenticated, region, error_message)
    """
    try:
        # Try to get the default session credentials
        session = boto3.Session()
        credentials = session.get_credentials()

        if not credentials:
            # Check if credentials file exists but no active session
            if os.path.exists(os.path.expanduser('~/.aws/credentials')):
                return False, None, ("No active AWS session found.\n"
                                   "Please start a new AWS session using Leapp or saml2aws (etc).\n"
                                   "e.g. If using Leapp, run 'leapp session start' to start a new session.")
            else:
                return False, None, "No AWS credentials found. Please run 'aws configure' to set up your credentials."

        # Get the current region
        region = session.region_name
        if not region:
            return False, None, "No AWS region configured. Please run 'aws configure' to set up your region."

        # Verify session is active by making a simple API call
        try:
            sts = session.client('sts')
            identity = sts.get_caller_identity()
            return True, region, None

        except botocore.exceptions.ClientError as e:
            if 'expired' in str(e).lower():
                return False, None, ("AWS session has expired.\n"
                                   "Please refresh your session using Leapp or saml2aws (etc).\n"
                                   "e.g. If using Leapp, run 'leapp session start' to start a new session.")
            elif 'not authorized' in str(e).lower():
                return False, None, ("Your AWS credentials don't have the required permissions.\n"
                                   "Please ensure you have the necessary IAM permissions for Bedrock.")
            else:
                return False, None, f"AWS authentication error: {str(e)}"

    except botocore.exceptions.ProfileNotFound:
        return False, None, ("AWS profile not found.\n"
                           "If using Leapp, ensure you have an active session. "
                           "Run 'leapp session start' to start a new session.")
    except botocore.exceptions.NoCredentialsError:
        if os.path.exists(os.path.expanduser('~/.aws/credentials')):
            return False, None, ("Found AWS credentials but no active session.\n"
                               "Please start a new AWS session using Leapp or saml2aws (etc).\n"
                               "e.g. If using Leapp, run 'leapp session start' to start a new session.")
        else:
            return False, None, "No AWS credentials found. Please run 'aws configure' to set up your credentials."

class BedrockClientError(Exception):
    """Base exception class for BedrockClient errors"""
    pass

class MaxRetriesExceeded(BedrockClientError):
    """Raised when max retries are exceeded"""
    pass

class BedrockStreamWrapper:
    """Wraps the Bedrock stream response to handle streaming content"""
    def __init__(self, stream_response):
        self.stream = stream_response.get('body')

    def __iter__(self):
        for event in self.stream:
            chunk = json.loads(event['chunk']['bytes'].decode())
            yield BedrockChunkWrapper(chunk)

class BedrockChunkWrapper:
    """Wraps individual chunks from the stream"""
    def __init__(self, chunk):
        if 'type' in chunk:
            self.type = chunk['type']
        else:
            self.type = 'content_block_delta'

        if 'delta' in chunk:
            self.delta = BedrockDeltaWrapper(chunk['delta'])
        else:
            content = chunk.get('content', [{'text': ''}])[0]
            self.delta = BedrockDeltaWrapper({'text': content.get('text', '')})

class BedrockDeltaWrapper:
    """Wraps the delta content from chunks"""
    def __init__(self, delta):
        self.text = delta.get('text', '')

class BedrockResponseWrapper:
    """Wraps non-streaming responses"""
    def __init__(self, response):
        content = response.get('content', [{'text': ''}])[0]
        self.content = [BedrockContentWrapper({'text': content.get('text', '')})]

class BedrockContentWrapper:
    """Wraps content from non-streaming responses"""
    def __init__(self, response):
        self.text = response.get('text', '')

class RetryingStreamIterator:
    """Implements retry logic for streaming responses"""
    def __init__(self, client, model_id, request_body, max_retries=3, base_delay=1.0, max_delay=20.0):
        self.client = client
        self.model_id = model_id
        self.request_body = request_body
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.attempt = 0
        self.current_stream = None
        self.current_iterator = None

    def _calculate_delay(self) -> float:
        """Calculate delay with exponential backoff and jitter"""
        exp_delay = min(self.max_delay, self.base_delay * (2 ** self.attempt))
        jitter = random.uniform(0, 0.1 * exp_delay)
        return exp_delay + jitter

    def _create_new_stream(self):
        """Create a new stream from the Bedrock client"""
        response = self.client.invoke_model_with_response_stream(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(self.request_body)
        )
        self.current_stream = BedrockStreamWrapper(response)
        self.current_iterator = iter(self.current_stream)

    def __iter__(self):
        return self

    def __next__(self):
        while self.attempt <= self.max_retries:
            try:
                if self.current_iterator is None:
                    self._create_new_stream()
                
                return next(self.current_iterator)

            except StopIteration:
                raise

            except (botocore.exceptions.EventStreamError, Exception) as e:
                if 'serviceunavailableexception' in str(e).lower():
                    if self.attempt < self.max_retries:
                        delay = self._calculate_delay()
                        print(f"\nService unavailable. Retrying stream in {delay:.2f} seconds (attempt {self.attempt + 1}/{self.max_retries})...")
                        time.sleep(delay)
                        self.attempt += 1
                        self.current_iterator = None  # Force creation of new stream
                        continue
                    else:
                        raise MaxRetriesExceeded(f"Maximum retries ({self.max_retries}) exceeded. Last error: {str(e)}")
                raise  # Re-raise any other exception

class BedrockClient:
    """Client for interacting with Amazon Bedrock"""
    def __init__(self, region_name=None, max_retries=3, base_delay=1.0, max_delay=20.0):
        try:
            if not region_name:
                session = boto3.Session()
                region_name = session.region_name
                if not region_name:
                    raise RuntimeError("No AWS region configured")

            self.client = boto3.client('bedrock-runtime', region_name=region_name)
            self.region = region_name
            self.max_retries = max_retries
            self.base_delay = base_delay
            self.max_delay = max_delay

        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'AccessDeniedException':
                raise RuntimeError("Access denied to Bedrock")
            elif e.response['Error']['Code'] == 'UnrecognizedClientException':
                raise RuntimeError("Invalid AWS credentials")
            else:
                raise RuntimeError(f"Error initializing Bedrock client: {str(e)}")
        except botocore.exceptions.EndpointConnectionError:
            raise RuntimeError(f"Could not connect to Bedrock in region {region_name}")

    def create_message(self, model_id: str, messages: list, system: Optional[str] = None,
                      max_tokens: Optional[int] = None, temperature: Optional[float] = None,
                      stream: bool = False):
        """Create a message with retry logic for ServiceUnavailable exceptions"""
        # Format messages for Bedrock
        formatted_messages = [
            {
                "role": msg["role"],
                "content": [{"type": "text", "text": msg["content"]}]
            }
            for msg in messages if msg.get("content")
        ]

        # Prepare request body
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": formatted_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature or 0.7
        }
        if system:
            request_body["system"] = system

        if stream:
            # Return a RetryingStreamIterator instead of creating the stream directly
            return RetryingStreamIterator(
                client=self.client,
                model_id=model_id,
                request_body=request_body,
                max_retries=self.max_retries,
                base_delay=self.base_delay,
                max_delay=self.max_delay
            )
        else:
            attempt = 0
            while attempt <= self.max_retries:
                try:
                    response = self.client.invoke_model(
                        modelId=model_id,
                        contentType="application/json",
                        accept="application/json",
                        body=json.dumps(request_body)
                    )
                    response_body = json.loads(response.get('body').read())
                    return BedrockResponseWrapper(response_body)
                
                except Exception as e:
                    if 'serviceunavailableexception' in str(e).lower():
                        if attempt < self.max_retries:
                            delay = min(self.max_delay, self.base_delay * (2 ** attempt))
                            jitter = random.uniform(0, 0.1 * delay)
                            total_delay = delay + jitter
                            print(f"\nService unavailable. Retrying in {total_delay:.2f} seconds (attempt {attempt + 1}/{self.max_retries})...")
                            time.sleep(total_delay)
                            attempt += 1
                            continue
                        else:
                            raise MaxRetriesExceeded(f"Maximum retries ({self.max_retries}) exceeded. Last error: {str(e)}")
                    raise

            return None  # Should never reach here due to raise statements

def ensure_chat_history_dir():
    """Ensures that the chat history base directory exists."""
    home_dir = os.path.expanduser("~")
    chat_history_base_dir = os.path.join(home_dir, '.wilma', 'chat-history', 'anthropic')
    os.makedirs(chat_history_base_dir, exist_ok=True)
    return chat_history_base_dir

def get_todays_chat_dir(chat_history_base_dir):
    """Returns today's chat directory, creating it if necessary."""
    today = datetime.now().strftime("%Y-%m-%d")
    todays_chat_dir = os.path.join(chat_history_base_dir, today)
    os.makedirs(todays_chat_dir, exist_ok=True)
    return todays_chat_dir

def save_chat(chat_data, chat_dir):
    global current_chat_file
    """Saves current chat data to the session file."""
    if not current_chat_file:
        time_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{time_stamp}.json"
        current_chat_file = os.path.join(chat_dir, filename)

    with open(current_chat_file, 'w', encoding='utf-8') as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=4)

def load_chat(file_path):
    """Loads chat data from a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def select_chat_file(chat_history_base_dir):
    """Provides a UI to select an old chat file from available files."""
    files = []
    for subdir, dirs, files_in_dir in os.walk(chat_history_base_dir):
        for file in files_in_dir:
            if file.endswith('.json'):
                full_path = os.path.join(subdir, file)
                files.append(full_path)
    files = sorted(files, reverse=True)[:20]

    if not files:
        print("No previous chats available.")
        return None

    console.print("[bold cyan]\nYour 20 most recent chats with Anthropic models, sorted by most recent first:[/]")
    for idx, file in enumerate(files):
        display_name = os.path.splitext(os.path.basename(file))[0]
        print(f"{idx + 1}) {display_name}")

    print("\nSelect a file to resume (number), or press Enter for the most recent chat: ")
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

def main_menu():
    """Show the main menu to the user and handle the choice."""
    first_menu = ("\n1) Start New Chat\n2) Resume Recent Chat")
    console.print(f"[bold blue]{first_menu}[/]")
    choice = input("\nChoose (1-2): ")
    return choice.strip()

def get_user_input() -> str:
    """Display the prompt to the user for multiline input.
    The user can press Esc followed by Enter to submit their input."""
    text = HTML('<u><b><style fg="ansiblue">User:</style></b></u>')
    user_input = prompt(print_formatted_text(text), multiline=True)
    return user_input

def detect_file_analysis_request(content: str) -> tuple[bool, str, bool]:
    if content.startswith("Upload:"):
        path = content[len("Upload: "):].strip()
        path = os.path.expanduser(path)
        if os.path.isdir(path):
            return True, path, True  # Indicates a directory
        return True, path, False  # Indicates a file
    return False, "", False

def should_ignore(file_path):
    ignore_patterns = [
        '*/.terraform/*', '.terraform',
        '*/.terragrunt-cache/*', '.terragrunt-cache',
        '*.tfstate', '*.tfstate*',
        '*/.tfsec/*', '.tfsec',
        '.vmc-makefile', '*/.centralized-makefile',
        'Pipfile', '*/Pipfile', 'Pipfile.lock', '*/Pipfile.lock',
        '.test-plans', '*/.test-plans', '.cache', '*/.cache',
        '*.pyc', '*/*.pyc', '*.pyo', '*/*.pyo', '*.zip', '*/*.zip',
        '__pycache__', '*/__pycache__', '.tox', '*/.tox',
        '*.egg-info', '*/*.egg-info', '.coverage', '*/.coverage',
        '.pytest_cache', '*/.pytest_cache', 'nosetests.xml', '*/nosetests.xml',
        'coverage.xml', '*/coverage.xml', 'htmlcov/', '*/htmlcov/',
        'report.xml', '*/report.xml', 'build/*', '*/build/*', 'dist/*',
        '*/dist/*', 'test-generated*.yml', '*/test-generated*.yml',
        '.DS_Store', '._.DS_Store', '.librarian', '.idea', '.vscode',
        '.history', '*swp', '.envrc', '.direnv', '.editorconfig',
        '.external_modules', 'modules/*', '.terraform.lock.hcl', '*.png',
        '*.jpg', '*.jpeg', '*.bmp', '.test-data', '*.plan', '*plan.out',
        '*plan.summary', '*/.git/hooks', '*/.git/info', '*/.git/logs',
        '*/.git/objects', '*/.git/refs', '*/.gitignore', '*/.git-credentials',
        '*/manifest.json', '.checkov.yaml', '*/saml/*'
    ]
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False

def is_binary(file_path):
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)  # Read the first 1024 bytes
            return b'\x00' in chunk  # Look for a NULL byte
    except Exception:
        return True  # If there's an error reading the file, treat it as binary

def get_directory_tree_structure(dir_path: str) -> str:
    """Returns the output of `tree -d` command on the specified directory path"""
    command = ["tree", "-d", dir_path]
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute `tree -d` on {dir_path}: {e}")
        return ""

def generate_markdown_from_directory(root_dir) -> tuple[str, int]:
    markdown_output = ""
    token_count = 0

    tree_structure = get_directory_tree_structure(root_dir)
    markdown_output += (f"# Directory Analysis for {root_dir}\n\n"
                        f"## Directory Structure as shown by the output of the `tree -d` command\n\n"
                        f"```\n{tree_structure}\n```\n\n")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not should_ignore(os.path.join(dirpath, d))]
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            relative_file_path = os.path.relpath(file_path, start=root_dir)
            if not should_ignore(file_path) and not is_binary(file_path):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                    enclosure = "```"
                    if filename.endswith('.md'):
                        enclosure = '"""'

                    markdown_output += f"## {relative_file_path}\n\n{enclosure}\n{content}\n{enclosure}\n\n"
                    token_count = estimate_token_count(markdown_output)
                    if token_count > 100000:
                        markdown_output = "DIRECTORY TOO BIG."

    return markdown_output, token_count

def read_file_contents(file_path: str) -> tuple[str, str, int]:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            file_name = os.path.basename(file_path)
            file_contents = file.read()
            if not file_contents:
                return file_name, False, 0
            token_count = estimate_token_count(file_contents)
            if token_count > 64000:
                return file_name, "FILE TOO BIG.", token_count
            return file_name, file_contents, token_count
    except Exception as e:
        print(f"\nError reading file: {e}")
        return "", 'I attempted to upload a file but it failed. For your next response reply ONLY: "No file was uploaded."', 0

def estimate_token_count(content: str) -> int:
    """Returns the number of tokens as an int."""
    encoding = tiktoken.encoding_for_model("gpt-4")
    num_tokens = len(encoding.encode(content))
    return num_tokens

def should_exit(content: str) -> bool:
    return content.lower() == "exit"

def append_message(messages: list, role: str, content: str):
    messages.append({"role": role, "content": content})

def select_model(debug=False):
    """
    Present user with a list of available Anthropic models and handle selection.
    Only shows models that are both available in the current region and configured.
    """
    try:
        with Halo(text='Checking Anthropic models available to you in this region...', spinner='dots') as spinner:
            models = get_available_models(debug=debug)
            if not models:
                spinner.stop()
                console.print("[bold red]No Anthropic models are currently available in your region or you lack permissions to access them.[/]")
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
                    sys.exit(0)
                except SystemExit:
                    os._exit(0)
    except Exception as e:
        console.print(f"[bold red]Error selecting model: {e}[/]")
        sys.exit(1)

def check_default_model(default_model, region, debug=False):
    """
    Check if the default model is available and accessible.
    If not, fall back to model selection.
    """
    with Halo(text='Checking default model...', spinner='dots') as spinner:
        runtime_client = boto3.client('bedrock-runtime', region_name=region)
        if not get_model_config(default_model):
            spinner.stop()
            console.print("[yellow]Default model not configured. Falling back to model selection...[/]")
            return select_model(debug=debug)

        if check_model_access(runtime_client, default_model, debug):
            return default_model

        spinner.stop()
        console.print("[yellow]Default model not available. Falling back to model selection...[/]")
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
            console.print("[yellow]Warning: ~/.wilma/config exists but is not readable[/]")
            return None

        # Check file size
        if os.path.getsize(config_path) > 1024:  # Arbitrary 1KB limit
            console.print("[yellow]Warning: ~/.wilma/config is suspiciously large[/]")
            return None

        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                if line.startswith('default_model'):
                    # Extract the model name between quotes
                    parts = line.split('=', 1)  # Split on first = only
                    if len(parts) != 2:
                        continue

                    model = parts[1].strip().strip('"\'')

                    # Validate model name format
                    if not model.startswith('anthropic.'):
                        console.print("[yellow]Warning: Invalid model name format in ~/.wilma/config[/]")
                        return None

                    # Check for suspicious characters
                    if any(char in model for char in ';&|$<>{}[]\\'):
                        console.print("[yellow]Warning: Suspicious characters in model name in ~/.wilma/config[/]")
                        return None

                    # Optional: Check if this model exists in our known models
                    if not get_model_config(model):
                        console.print("[yellow]Warning: Unknown model specified in ~/.wilma/config[/]")
                        return None

                    return model

        return None

    except UnicodeDecodeError:
        console.print("[yellow]Warning: ~/.wilma/config is not a valid text file[/]")
        return None
    except Exception as e:
        if str(e):  # Only print if there's an actual error message
            console.print(f"[yellow]Warning: Error reading ~/.wilma/config: {str(e)}[/]")
        return None

def parse_arguments():
    parser = argparse.ArgumentParser(
        description=("Universal Chatbot - Chat with Anthropic's Claude models "
            "\nUse your own Anthropic API key to chat with their latest LLMs."),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-m", "--model-select",
        nargs='?',
        const='show_menu',
        metavar="MODEL",
        help="Select the Anthropic (via Amazon Bedrock) model to use. Options:\n"
             "  - Specify a model name directly\n"
             "  - Use without a value to select from a list of models available in your authenticated AWS region\n"
             "  - Omit to use the default model (claude-3-5-sonnet-20241022)\n"
    )
    parser.add_argument(
        "-ws", "--web-search",
        action='store_true',
        help="Enable web search functionality for answering queries."
    )
    parser.add_argument(
        "--debug",
        action='store_true',
        help="Enable debug output"
    )
    return parser.parse_args()

def perform_web_search(query):
    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
    if not perplexity_api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is not set")

    now = datetime.now()
    local_date = now.strftime("%a %d %b %Y")
    local_time = now.strftime("%H:%M:%S %Z")

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {perplexity_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-sonar-huge-128k-online",
        "messages": [
            {
                "role": "system",
                "content": "Be awesome. Think carefully."
            },
            {
                "role": "user",
                "content": query
            }
        ],
        "temperature": 0.3
    }

    response = requests.request("POST", url, json=payload, headers=headers)

    if response.status_code == 200:
        content = response.json()['choices'][0]['message']['content'].strip()
        return f"Found online today, {local_date}, at time {local_time}: {content}"
    else:
        raise Exception(f"Error from Perplexity API: {response.status_code} - {response.text}")

def should_perform_web_search(content, selected_model, model_config, client):
    """
    Consult Claude to decide if a web search is beneficial.
    """
    decision_prompt = (
        f"As an advanced AI model, analyze the following query and decide if it would benefit from real-time information via a web search. "
        f"If yes, respond with 'YES: <query>'. If not, respond with 'NO'.\n\n"
        f"Content: \"{content}\""
    )
    system_prompt = "Assess if user queries require external web search to enhance responses."

    response = client.create_message(
        model_id=selected_model,
        messages=[{"role": "user", "content": decision_prompt}],
        system=system_prompt,
        max_tokens=50,
        temperature=model_config["temperature"]
    )

    response_text = response.content[0].text.strip()
    if response_text.startswith("YES:"):
        search_query = response_text.replace("YES: ", "")
        return True, search_query
    else:
        return False, ""

def check_web_search_availability(web_search_requested):
    """
    Check if web search is available based on environment variables and user request.
    Returns whether web search should be enabled.
    """
    if not web_search_requested:
        return False

    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
    if not perplexity_api_key:
        console.print("[yellow]Web search feature is not available: PERPLEXITY_API_KEY environment variable is not set.[/]")
        console.print("[yellow]Continuing in normal mode...[/]")
        return False

    return True

def main():
    is_authenticated, region, error_message = check_aws_authentication()

    if not is_authenticated:
        console.print(f"[bold red]AWS Authentication Error: {error_message}[/]")
        sys.exit(1)

    console.print(f"[bold green]Authenticated with AWS in region: {region}[/]")

    args = parse_arguments()
    web_search_enabled = check_web_search_availability(args.web_search)
    system_default_model = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    if args.model_select:
        if args.model_select == 'show_menu':
            selected_model = select_model(debug=args.debug)
        elif args.model_select in get_model_list(debug=args.debug):
            selected_model = args.model_select
        else:
            print(f"Invalid model: {args.model_select}")
            selected_model = select_model(debug=args.debug)
    else:
        # Check for user-defined default model
        user_default = get_user_default_model()
        default_model = user_default if user_default else system_default_model
        
        selected_model = check_default_model(default_model, region, debug=args.debug)

    model_config = get_model_config(selected_model)
    friendly_name = model_config["friendly_name"]
    training_cutoff = model_config["training_cutoff"]
    client = BedrockClient(
        region_name=region,
        max_retries=6,
        base_delay=1.0,
        max_delay=20.0
    )
    web_search_enabled = args.web_search

    try:
        # Initialise and ensure chat history directories
        chat_history_base_dir = ensure_chat_history_dir()
        todays_chat_dir = get_todays_chat_dir(chat_history_base_dir)

        now = datetime.now()
        local_date = now.strftime("%a %d %b %Y")
        local_time = now.strftime("%H:%M:%S %Z")

        system_prompt = (f"Specifically, your model is \"{friendly_name}\". Your knowledge base was last updated "
                        f"in {training_cutoff}. Today is {local_date}. Local time is {local_time}. You write in British "
                        f"English and you are not too quick to apologise or thank the user. You MUST format your "
                        f"responses in Markdown syntax. Use `- ` for any unnumbered bullet point lists, as per "
                        f"standard Markdown syntax.")

        choice = main_menu()
        if choice == "2":
            chat_file = select_chat_file(chat_history_base_dir)
            if chat_file:
                messages = load_chat(chat_file)
            else:
                print("No chat selected or file not found.")
                return
        else:
            messages = []

        welcome = f"""
You're now chatting with {friendly_name} via Amazon Bedrock.
The user prompt handles multiline input, so Enter gives a newline.
To submit your prompt hit Esc -> Enter.
To exit gracefully simply submit the word: "exit", or hit Ctrl+C.

You can pass individual utf-8 encoded files by entering "Upload: ~/path/to/file_name"
You can pass entire directories (recursively) by entering "Upload: ~/path/to/directory"
"""

        console.print(f"[bold blue]{welcome}[/]")

        while True:
            content = get_user_input()

            if should_exit(content):
                break

            console.print(f"\n[yellow underline]{friendly_name}:[/]")
            is_file_request, path, is_directory = detect_file_analysis_request(content)
            if is_file_request:
                if is_directory:
                    markdown_content, token_count = generate_markdown_from_directory(path)
                    if markdown_content == "DIRECTORY TOO BIG.":
                        print(f"\nThe directory is too large to upload because it is likely larger than 100,000 tokens.\n"
                              f"Estimated token count for this recursive directory analysis: {token_count}\n")
                    if markdown_content:
                        dir_analysis_request = (f"The following describes a directory structure along with all its contents in "
                                              f"Markdown format. "
                                              f"Please carefully analyse the directory structure and the files contained within. Pay "
                                              f"attention to whether the directory structure looks like a code repository. Then take a "
                                              f"deep breath and provide a brief summary of your analysis. End your response with an "
                                              f"assurance that you have memorised the contents of the repository and you are ready to "
                                              f"answer the user's questions.\n\n{markdown_content}")
                        append_message(messages, "user", dir_analysis_request)
                        print(f"\nEstimated token count for this recursive directory analysis: {token_count}\n")
                    else:
                        print_formatted_text(HTML("<ansired>Directory is empty or contains no readable files.</ansired>"))
                        continue
                else:
                    file_name, file_contents, token_count = read_file_contents(path)
                    if file_contents == "FILE TOO BIG.":
                        print(f"\nThe file: {file_name} is too large to upload because it is likely larger than 64,000 tokens.\n"
                              f"Estimated token count for this file: {token_count}\n")
                    elif file_contents:
                        file_analysis_request = (f"Please analyse the contents of the following file:\n"
                                               f"\n{file_name}\n"
                                               f"\n{file_contents}\n"
                                               f"\nEnd your response by asking the user what questions they have about the file.")
                        append_message(messages, "user", file_analysis_request)
                        print(f"\nEstimated token count for this file: {token_count}\n")
                    else:
                        print_formatted_text(HTML(f"\nThe file: {file_name} is empty.\n"))
                        print(f"Estimated token count for this file: {token_count}\n")
                        continue
            else:
                append_message(messages, "user", content)

                if web_search_enabled:
                    web_search_needed, search_query = should_perform_web_search(content, selected_model, model_config, client)

                    response_content = ""
                    if web_search_needed:
                        print("Web search in progress...\n")
                        try:
                            web_search_results = perform_web_search(search_query)
                            response_content += f"<web-search-results> {web_search_results} </web-search-results>"
                        except Exception as e:
                            print(f"Error during web search: {e}")

                    if response_content:
                        append_message(messages, "assistant", response_content)
                        websearch_analysis_request = ("Thank you for carrying out a web search on my behalf with Perplexity. "
                            "The results of the Perplexity web search are contained in the <web-search-results> XML tag in your previous assistant content. "
                            "You will now take ownership of those <web-search-results> and present them to me, the user, as your own 'research'. "
                            "Now reflect on those <web-search-results> to augment and inform your own training data as you carefully provide an "
                            "excellent answer to my original query. Keep these <web-search-results> in mind as we continue our conversation.")

                        append_message(messages, "user", websearch_analysis_request)

            supports_streaming = model_config.get("supports_streaming", True)

            if supports_streaming:
                stream = client.create_message(
                    model_id=selected_model,
                    messages=messages,
                    system=system_prompt,
                    max_tokens=model_config["max_tokens"],
                    temperature=model_config["temperature"],
                    stream=True
                )

                complete_message = ""
                with Live(Markdown(complete_message),
                          refresh_per_second=10,
                          console=console,
                          transient=False) as live:
                    for chunk in stream:
                        if chunk.type == "content_block_delta":
                            if chunk.delta.text:
                                complete_message += chunk.delta.text
                                live.update(Markdown(complete_message))
                        elif chunk.type == "message_stop":
                            break
            else:
                response = client.create_message(
                    model_id=selected_model,
                    messages=messages,
                    system=system_prompt,
                    max_tokens=model_config["max_tokens"],
                    temperature=model_config["temperature"]
                )
                complete_message = response.content[0].text
                console.print(Markdown(complete_message))

            append_message(messages, "assistant", complete_message)

            print("\n")
            print(Rule(), "")

            save_chat(messages, todays_chat_dir)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

if __name__ == "__main__":
    main()