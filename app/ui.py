#!/usr/bin/env python3

import os

from prompt_toolkit import prompt
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.markdown import Markdown
from rich.rule import Rule
from rich.padding import Padding
from rich.style import Style
from rich.text import Text
from code_blocks import (                                                                                                                                                                                                                                  
    process_markdown_for_code_blocks,                                                                                                                                                                                                                      
    handle_copy_command,                                                                                                                                                                                                                                   
    get_copy_help_text,                                                                                                                                                                                                                                    
    reset_code_blocks                                                                                                                                                                                                                                      
) 

console = Console(highlight=False)


def main_menu():
    """Show the main menu to the user and handle the choice."""
    first_menu = "\n1) Start New Chat\n2) Resume Recent Chat"
    console.print(f"[bold blue]{first_menu}[/]")
    choice = input("\nChoose (1-2): ")
    return choice.strip()

                                                                                                                                                                                             
def get_user_input() -> str:                                                                                                                                                                                                                               
    """Display the prompt to the user for multiline input.                                                                                                                                                                                                 
    The user can press Esc followed by Enter to submit their input."""                                                                                                                                                                                     
    text = HTML('<u><b><style fg="ansiblue">User:</style></b></u>')                                                                                                                                                                                        
                                                                                                                                                                                                                                                        
    while True:                                                                                                                                                                                                                                            
        user_input = prompt(print_formatted_text(text), multiline=True)                                                                                                                                                                                                                                                                                                                                                                                                     
        if handle_copy_command(user_input):                                                                                                                                                                                                                
            continue                                                                                                                                                                                        
                                                                                                                                                                                                                                                        
        return user_input 


def show_welcome_message(model_name):                                                                                                                                                                                                                      
    """Display a welcome message with instructions."""                                                                                                                                                                                                     
    welcome = f"""                                                                                                                                                                                                                                         
You're now chatting with {model_name} via Amazon Bedrock.                                                                                                                                                                                                  
The user prompt handles multiline input, so Enter gives a newline.                                                                                                                                                                                         
To submit your prompt hit Esc -> Enter.                                                                                                                                                                                                                    
To exit gracefully simply submit the word: "exit", or hit Ctrl+C.                                                                                                                                                                                          
                                                                                                                                                                                                                                                        
You can pass individual utf-8 encoded files by entering "Upload: ~/path/to/file_name"                                                                                                                                                                      
You can pass entire directories (recursively) by entering "Upload: ~/path/to/directory"                                                                                                                                                                    
                                                                                                                                                                                                                                                        
When code blocks appear in responses, you can copy them by typing "copy #"                                                                                                                                                                                 
where # is the number shown next to the code block (e.g., "copy 1").                                                                                                                                                                                       
"""                                                                                                                                                                                                                                                        
    console.print(f"[bold blue]{welcome}[/]")


def show_loading_message(message="Working..."):
    """Display a loading message."""
    console.print(f"[yellow]{message}[/]")


def show_error_message(message):
    """Display an error message."""
    console.print(f"[bold red]Error: {message}[/]")


def show_warning_message(message):
    """Display a warning message."""
    console.print(f"[yellow]{message}[/]")


def show_success_message(message):
    """Display a success message."""
    console.print(f"[bold green]{message}[/]")


def show_info_message(message):
    """Display an info message."""
    console.print(f"[blue]{message}[/]")


def format_message_as_bubble(content, is_user=False, model_name="Assistant"):
    """Format a message as a chat bubble, aligned right for user and left for assistant."""
    bubble_width = int(console.width * 0.8)

    if not is_user:                                                                                                                                                                                                                                        
        formatted_content = process_markdown_for_code_blocks(content)                                                                                                                                                                                      
    else:                                                                                                                                                                                                                                                  
        formatted_content = content

    markdown_content = Markdown(formatted_content)

    if is_user:
        panel = Panel(
            markdown_content,
            border_style="blue",
            padding=(1, 2),
            title="You",
            title_align="right",
            width=bubble_width,
            highlight=True,
        )
        return Align.right(panel)
    else:
        panel = Panel(
            markdown_content,
            border_style="green",
            padding=(1, 2),
            title=model_name,
            title_align="left",
            width=bubble_width,
            highlight=True,
        )
        return Align.left(panel)


def render_chat_history(messages, model_name="Assistant"):                                                                                                                                                                                                 
    """Render the entire chat history with bubbles."""                                                                                                                                                                                                     
    message_groups = []                                                                                                                                                                                                                                                                                                                                                                                                                                               
    reset_code_blocks()                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                        
    for msg in messages:                                                                                                                                                                                                                                   
        if msg["role"] == "user" and msg.get("content"):                                                                                                                                                                                                   
            message_groups.append(                                                                                                                                                                                                                         
                format_message_as_bubble(msg["content"], is_user=True)                                                                                                                                                                                     
            )                                                                                                                                                                                                                                              
        elif msg["role"] == "assistant" and msg.get("content"):                                                                                                                                                                                                 
            message_groups.append(                                                                                                                                                                                                                         
                format_message_as_bubble(                                                                                                                                                                                                                  
                    msg["content"], is_user=False, model_name=model_name                                                                                                                                                                                   
                )                                                                                                                                                                                                                                          
            )                                                                                                                                                                                                                                              
                                                                                                                                                                                                                      
    return Padding(Rule(), (1, 0)).join(message_groups)


def display_chat_history(messages, model_name="Assistant"):
    """Display the chat history in the console."""
    console.print(render_chat_history(messages, model_name))


def display_model_list(models, model_configs):
    """Display a list of available models."""
    console.print("[bold blue]\nAvailable models:[/]")
    for idx, model in enumerate(models, 1):
        friendly_name = model_configs[model]["friendly_name"]
        console.print(f"[bold blue]{idx}) {friendly_name}[/]")


def select_model_from_list(models, model_configs):
    """Let the user select a model from a list."""
    display_model_list(models, model_configs)

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
            import sys

            sys.exit(0)


def display_chat_files(files):
    """Display a list of chat files."""
    console.print(
        "[bold cyan]\nYour 20 most recent chats, sorted by most recent first:[/]"
    )
    for idx, file in enumerate(files):
        display_name = os.path.splitext(os.path.basename(file))[0]
        print(f"{idx + 1}) {display_name}")


def select_chat_file_from_list(files):
    """Let the user select a chat file from a list."""
    display_chat_files(files)

    print(
        "\nSelect a file to resume (number), or press Enter for the most recent chat: "
    )
    user_input = input().strip()

    if user_input == "":
        return files[0] if files else None

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


def display_streaming_response(stream, model_config):                                                                                                                                                                                                      
    """Display a streaming response from the model."""                                                                                                                                                                                                     
    complete_message = ""                                                                                                                                                                                                                                  
    with console.status("[bold green]Thinking...", spinner="dots") as status:                                                                                                                                                                              
        for chunk in stream:                                                                                                                                                                                                                               
            if chunk.type == "content_block_delta":                                                                                                                                                                                                        
                if chunk.delta.text:                                                                                                                                                                                                                       
                    complete_message += chunk.delta.text                                                                                                                                                                                                                                                                                                                                                                                
                    if len(complete_message) == len(chunk.delta.text):                                                                                                                                                                                     
                        status.stop()                                                                                                                                                                                                                      
                    console.print(Markdown(complete_message), end="")                                                                                                                                                                                      
            elif chunk.type == "message_stop":                                                                                                                                                                                                             
                break                                                                                                                                                                                                                                                                                                                                                                                                                                                          
    console.print()                                                                                                                                                                                                                                                                                                                                                                                                                                            
    processed_message = process_markdown_for_code_blocks(complete_message)                                                                                                                                                                                                                                                                                                                                                                                  
    help_text = get_copy_help_text()                                                                                                                                                                                                                       
    if help_text:                                                                                                                                                                                                                                          
        console.print(help_text)                                                                                                                                                                                                                           
                                                                                                                                                                                                                                                        
    return processed_message


def clear_screen():
    """Clear the terminal screen."""
    import os

    os.system("cls" if os.name == "nt" else "clear")


def enable_bubble_mode():
    """Enable bubble UI mode for messages."""
    import os

    os.environ["WILMA_UI_MODE"] = "bubble"


def disable_bubble_mode():
    """Disable bubble UI mode for messages."""
    import os

    if "WILMA_UI_MODE" in os.environ:
        del os.environ["WILMA_UI_MODE"]


def is_bubble_mode_enabled():
    """Check if bubble UI mode is enabled."""
    import os

    return os.environ.get("WILMA_UI_MODE") == "bubble"


def display_message(content, is_user=False, model_name="Assistant"):                                                                                                                                                                                       
    """Display a message using the current UI mode with copyable code blocks."""                                                                                                                                                                           
    if not is_user:                                                                                                                                                                                                                                                                                                                                                                                                                                  
        formatted_content = process_markdown_for_code_blocks(content)                                                                                                                                                                                      
    else:                                                                                                                                                                                                                                                  
        formatted_content = content                                                                                                                                                                                                                                                                                                                                                                                                                           
    if is_bubble_mode_enabled():                                                                                                                                                                                                                           
        console.print(format_message_as_bubble(formatted_content, is_user, model_name))                                                                                                                                                                    
    else:                                                                                                                                                                                                                                                  
        if is_user:                                                                                                                                                                                                                                        
            console.print("\n[bold blue]User:[/]")                                                                                                                                                                                                         
        else:                                                                                                                                                                                                                                              
            console.print(f"\n[bold green]{model_name}:[/]")                                                                                                                                                                                               
        console.print(Markdown(formatted_content))                                                                                                                                                                                                                                                                                                                                                                                                                
    if not is_user:                                                                                                                                                                                                                                        
        help_text = get_copy_help_text()                                                                                                                                                                                                                   
        if help_text:                                                                                                                                                                                                                                      
            console.print(help_text) 