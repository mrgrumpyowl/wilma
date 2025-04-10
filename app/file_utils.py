#!/usr/bin/env python3

import fnmatch
import os
import subprocess
import tiktoken
from typing import Tuple, List, Optional
from rich.console import Console

console = Console(highlight=False)


def detect_file_analysis_request(content: str) -> Tuple[bool, str, bool]:
    """
    Detect if the user is requesting file analysis.
    Returns a tuple of (is_file_request, path, is_directory)
    """
    if content.startswith("Upload:"):
        path = content[len("Upload: ") :].strip()
        path = os.path.expanduser(path)
        if os.path.isdir(path):
            return True, path, True  # Indicates a directory
        return True, path, False  # Indicates a file
    return False, "", False


def should_ignore(file_path: str) -> bool:
    """
    Check if a file should be ignored during directory analysis.
    Returns True if the file should be ignored, False otherwise.
    """
    ignore_patterns = [
        "*/.terraform/*",
        ".terraform",
        "*/.terragrunt-cache/*",
        ".terragrunt-cache",
        "*.tfstate",
        "*.tfstate*",
        "*/.tfsec/*",
        ".tfsec",
        ".vmc-makefile",
        "*/.centralized-makefile",
        "Pipfile",
        "*/Pipfile",
        "Pipfile.lock",
        "*/Pipfile.lock",
        ".test-plans",
        "*/.test-plans",
        ".cache",
        "*/.cache",
        "*.pyc",
        "*/*.pyc",
        "*.pyo",
        "*/*.pyo",
        "*.zip",
        "*/*.zip",
        "__pycache__",
        "*/__pycache__",
        ".tox",
        "*/.tox",
        "*.egg-info",
        "*/*.egg-info",
        ".coverage",
        "*/.coverage",
        ".pytest_cache",
        "*/.pytest_cache",
        "nosetests.xml",
        "*/nosetests.xml",
        "coverage.xml",
        "*/coverage.xml",
        "htmlcov/",
        "*/htmlcov/",
        "report.xml",
        "*/report.xml",
        "build/*",
        "*/build/*",
        "dist/*",
        "*/dist/*",
        "test-generated*.yml",
        "*/test-generated*.yml",
        ".DS_Store",
        "._.DS_Store",
        ".librarian",
        ".idea",
        ".vscode",
        ".history",
        "*swp",
        ".envrc",
        ".direnv",
        ".editorconfig",
        ".external_modules",
        "modules/*",
        ".terraform.lock.hcl",
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.bmp",
        ".test-data",
        "*.plan",
        "*plan.out",
        "*plan.summary",
        "*/.git/hooks",
        "*/.git/info",
        "*/.git/logs",
        "*/.git/objects",
        "*/.git/refs",
        "*/.gitignore",
        "*/.git-credentials",
        "*/manifest.json",
        ".checkov.yaml",
        "*/saml/*",
    ]
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False


def is_binary(file_path: str) -> bool:
    """
    Check if a file is binary.
    Returns True if the file is binary, False otherwise.
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)  # Read the first 1024 bytes
            return b"\x00" in chunk  # Look for a NULL byte
    except Exception:
        return True  # If there's an error reading the file, treat it as binary


def get_directory_tree_structure(dir_path: str) -> str:
    """
    Returns the output of `tree -d` command on the specified directory path.
    """
    command = ["tree", "-d", dir_path]
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute `tree -d` on {dir_path}: {e}")
        return ""


def generate_markdown_from_directory(root_dir: str) -> Tuple[str, int]:
    """
    Generate markdown representation of a directory.
    Returns a tuple of (markdown_content, token_count)
    """
    markdown_output = ""
    token_count = 0

    tree_structure = get_directory_tree_structure(root_dir)
    markdown_output += (
        f"# Directory Analysis for {root_dir}\n\n"
        f"## Directory Structure as shown by the output of the `tree -d` command\n\n"
        f"```\n{tree_structure}\n```\n\n"
    )

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [
            d for d in dirnames if not should_ignore(os.path.join(dirpath, d))
        ]
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            relative_file_path = os.path.relpath(file_path, start=root_dir)
            if not should_ignore(file_path) and not is_binary(file_path):
                try:
                    with open(
                        file_path, "r", encoding="utf-8", errors="ignore"
                    ) as file:
                        content = file.read()
                        enclosure = "```"
                        if filename.endswith(".md"):
                            enclosure = '"""'

                        markdown_output += f"## {relative_file_path}\n\n{enclosure}\n{content}\n{enclosure}\n\n"
                        token_count = estimate_token_count(markdown_output)
                        if token_count > 100000:
                            return "DIRECTORY TOO BIG.", token_count
                except Exception as e:
                    console.print(
                        f"[yellow]Warning: Could not read file {file_path}: {str(e)}[/]"
                    )

    return markdown_output, token_count


def read_file_contents(file_path: str) -> Tuple[str, str, int]:
    """
    Read the contents of a file.
    Returns a tuple of (file_name, file_contents, token_count)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            file_name = os.path.basename(file_path)
            file_contents = file.read()
            if not file_contents:
                return file_name, "", 0
            token_count = estimate_token_count(file_contents)
            if token_count > 64000:
                return file_name, "FILE TOO BIG.", token_count
            return file_name, file_contents, token_count
    except Exception as e:
        console.print(f"[red]\nError reading file: {e}[/]")
        return (
            "",
            'I attempted to upload a file but it failed. For your next response reply ONLY: "No file was uploaded."',
            0,
        )


def estimate_token_count(content: str) -> int:
    """
    Returns the number of tokens in the content as an int.
    """
    try:
        encoding = tiktoken.encoding_for_model("gpt-4")
        num_tokens = len(encoding.encode(content))
        return num_tokens
    except Exception:
        # Fallback method if tiktoken fails
        # Rough estimate: 1 token ≈ 4 characters for English text
        return len(content) // 4


def get_file_extension(file_path: str) -> str:
    """
    Get the extension of a file.
    """
    _, ext = os.path.splitext(file_path)
    return ext.lower()


def is_text_file(file_path: str) -> bool:
    """
    Check if a file is a text file based on extension and content.
    """
    # Common text file extensions
    text_extensions = {
        ".txt",
        ".md",
        ".py",
        ".js",
        ".html",
        ".css",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".ini",
        ".conf",
        ".sh",
        ".bash",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".java",
        ".rb",
        ".pl",
        ".php",
        ".ts",
        ".go",
        ".rs",
        ".swift",
        ".kt",
        ".kts",
        ".scala",
        ".sc",
        ".groovy",
        ".gradle",
        ".sql",
        ".r",
        ".m",
        ".mm",
        ".f",
        ".f90",
        ".f95",
        ".for",
        ".tcl",
        ".lua",
        ".ps1",
        ".psm1",
        ".bat",
        ".cmd",
        ".vbs",
        ".tex",
        ".csv",
        ".tsv",
        ".log",
        ".cfg",
        ".properties",
        ".toml",
        ".dart",
        ".jsx",
        ".tsx",
        ".vue",
        ".svelte",
        ".elm",
        ".clj",
        ".edn",
        ".hs",
        ".lhs",
        ".tf",
        ".tfvars",
        ".hcl",
    }

    # Check extension first
    ext = get_file_extension(file_path)
    if ext in text_extensions:
        return True

    # If extension check is inconclusive, check content
    return not is_binary(file_path)


def list_directory_contents(
    dir_path: str, recursive: bool = False, include_hidden: bool = False
) -> List[str]:
    """
    List the contents of a directory.
    Returns a list of file paths.
    """
    file_list = []

    if recursive:
        for root, dirs, files in os.walk(dir_path):
            # Skip hidden directories if not included
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith(".")]

            for file in files:
                # Skip hidden files if not included
                if not include_hidden and file.startswith("."):
                    continue

                file_path = os.path.join(root, file)
                if not should_ignore(file_path):
                    file_list.append(file_path)
    else:
        # Non-recursive listing
        for item in os.listdir(dir_path):
            # Skip hidden items if not included
            if not include_hidden and item.startswith("."):
                continue

            item_path = os.path.join(dir_path, item)
            if not should_ignore(item_path):
                file_list.append(item_path)

    return file_list


def get_file_info(file_path: str) -> dict:
    """
    Get information about a file.
    Returns a dictionary with file information.
    """
    try:
        stat_info = os.stat(file_path)
        return {
            "path": file_path,
            "name": os.path.basename(file_path),
            "size": stat_info.st_size,
            "modified": stat_info.st_mtime,
            "is_dir": os.path.isdir(file_path),
            "is_file": os.path.isfile(file_path),
            "is_binary": is_binary(file_path) if os.path.isfile(file_path) else False,
            "extension": (
                get_file_extension(file_path) if os.path.isfile(file_path) else ""
            ),
        }
    except Exception as e:
        console.print(f"[red]Error getting file info for {file_path}: {str(e)}[/]")
        return {"path": file_path, "name": os.path.basename(file_path), "error": str(e)}
