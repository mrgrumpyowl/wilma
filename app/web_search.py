#!/usr/bin/env python3

import os
import requests
from datetime import datetime
from typing import Tuple, Optional, Dict, Any
from rich.console import Console

console = Console(highlight=False)


def perform_web_search(query: str) -> str:
    """
    Perform a web search using Perplexity API.
    Returns the search results as a string.

    Raises:
        ValueError: If PERPLEXITY_API_KEY environment variable is not set
        Exception: If the API request fails
    """
    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
    if not perplexity_api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is not set")

    # Get current date and time for context
    now = datetime.now()
    local_date = now.strftime("%a %d %b %Y")
    local_time = now.strftime("%H:%M:%S %Z")

    # Prepare API request
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {perplexity_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.1-sonar-huge-128k-online",
        "messages": [
            {"role": "system", "content": "Be awesome. Think carefully."},
            {"role": "user", "content": query},
        ],
        "temperature": 0.3,
    }

    # Make API request
    response = requests.request("POST", url, json=payload, headers=headers)

    # Process response
    if response.status_code == 200:
        content = response.json()["choices"][0]["message"]["content"].strip()
        return f"Found online today, {local_date}, at time {local_time}: {content}"
    else:
        raise Exception(
            f"Error from Perplexity API: {response.status_code} - {response.text}"
        )


def should_perform_web_search(
    content: str, selected_model: str, model_config: Dict[str, Any], client
) -> Tuple[bool, str]:
    """
    Consult Claude to decide if a web search is beneficial.
    Returns a tuple of (should_search, search_query)
    """
    decision_prompt = (
        f"As an advanced AI model, analyze the following query and decide if it would benefit from real-time information via a web search. "
        f"If yes, respond with 'YES: <query>'. If not, respond with 'NO'.\n\n"
        f'Content: "{content}"'
    )
    system_prompt = (
        "Assess if user queries require external web search to enhance responses."
    )

    response = client.create_message(
        model_id=selected_model,
        messages=[{"role": "user", "content": decision_prompt}],
        system=system_prompt,
        max_tokens=50,
        temperature=model_config["temperature"],
    )

    response_text = response.content[0].text.strip()
    if response_text.startswith("YES:"):
        search_query = response_text.replace("YES: ", "")
        return True, search_query
    else:
        return False, ""


def check_web_search_availability(web_search_requested: bool) -> bool:
    """
    Check if web search is available based on environment variables and user request.
    Returns whether web search should be enabled.
    """
    if not web_search_requested:
        return False

    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
    if not perplexity_api_key:
        console.print(
            "[yellow]Web search feature is not available: PERPLEXITY_API_KEY environment variable is not set.[/]"
        )
        console.print("[yellow]Continuing in normal mode...[/]")
        return False

    return True


def get_web_search_results(query: str) -> Optional[str]:
    """
    Get web search results for a query.
    Returns the search results as a string, or None if search is not available or fails.
    """
    try:
        if not os.getenv("PERPLEXITY_API_KEY"):
            return None

        console.print(f"[yellow]Web search in progress for: {query}...[/]")
        results = perform_web_search(query)
        return results
    except Exception as e:
        console.print(f"[red]Error during web search: {e}[/]")
        return None


def create_web_search_prompt(web_search_results: str) -> str:
    """
    Create a prompt to analyze web search results.
    Returns a prompt string.
    """
    return (
        "Thank you for carrying out a web search on my behalf with Perplexity. "
        "The results of the Perplexity web search are contained in the <web-search-results> XML tag in your previous assistant content. "
        "You will now take ownership of those <web-search-results> and present them to me, the user, as your own 'research'. "
        "Now reflect on those <web-search-results> to augment and inform your own training data as you carefully provide an "
        "excellent answer to my original query. Keep these <web-search-results> in mind as we continue our conversation."
    )


def format_web_search_results(results: str) -> str:
    """
    Format web search results for inclusion in a message.
    Returns a formatted string.
    """
    return f"<web-search-results> {results} </web-search-results>"


def process_web_search_for_query(
    query: str, client, model_id: str, model_config: Dict[str, Any]
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Process a web search for a query.
    Returns a tuple of (search_performed, search_results, analysis_prompt)
    """
    # Check if query would benefit from web search
    should_search, search_query = should_perform_web_search(
        query, model_id, model_config, client
    )

    if not should_search:
        return False, None, None

    # Perform web search
    search_results = get_web_search_results(search_query)

    if not search_results:
        return False, None, None

    # Format results and create analysis prompt
    formatted_results = format_web_search_results(search_results)
    analysis_prompt = create_web_search_prompt(formatted_results)

    return True, formatted_results, analysis_prompt
