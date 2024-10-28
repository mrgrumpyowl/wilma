# CLI Chat Interface for Anthropic's Claude LLMs

This project provides a simple CLI chat interface to interact with Anthropic's Claude models. It utilizes the `anthropic[bedrock]` Python package to communicate with Anthropic models via the Amazon Bedrock API and provides a user-friendly command-line interface for submitting prompts and receiving responses.

## Contributing

Contributions are welcome! If you have suggestions for improvements or bug fixes, feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Features

- Multiline input support for detailed prompts.
- Real-time response loading indicator.
- Graceful exit options.
- Enhanced output formatting with `rich` and `prompt_toolkit` libraries.
- Supports uploading individual files by entering "Upload: ~/path/to/file_name"
- Supports uploading an entire directory and its contents recursively by entering "Upload: ~/path/to/directory"
- Note that the upload features are designed primarily for code repository analysis so supports only utf-8 encoded files.
- Stores chat history in `~/.wilma/chat-history/` and can resume a previous conversation if the user desires.

## Prerequisites

Before you start, ensure you have installed the following:

- Python 3.10 or higher
- `anthropic` Python package
- `anthropic[bedrock]` Python package
- `prompt_toolkit` Python package
- `rich` Python package
- `tiktoken` Python package
- `tree` command-line utility

## Installation

### Manual
<!-- markdownlint-disable MD029-->
1. Clone this repository to your local machine.
2. Install the required Python packages by running:

```bash
pip3 install anthropic[bedrock] prompt_toolkit rich tiktoken
```

3. Set up your Amazon Bedrock access. Nice set of instructions [here](https://github.com/mrgrumpyowl/wilma.git) and [here](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock). 

## Usage

To start the chat interface, navigate to the directory containing the script and make it executable:

```bash
chmod +x wilma.py
```

Then you can just run it with:

```bash
./wilma.py
```

Follow the on-screen instructions for submitting prompts to Claude.

Nb. If you like the script and want to put it in the way of your PATH so that you can run it from wherever, just add a symbolic link pointing `/usr/local/bin`.

For example (on MacOS):

```bash
sudo ln -s /Users/username/mrgrumpyowl/wilma/wilma.py /usr/local/bin/wilma
```

### Pip install

Latest:

```bash
pip3 install git+https://github.com/mrgrumpyowl/wilma.git@master --upgrade
```

Specific Version:

```bash
pip3 install git+https://github.com/mrgrumpyowl/wilma.git@1.0.0 --upgrade
```

Whatever the code currently looks like while you're developing it (and assuming you're cd'd into this directory):

```bash
pip3 uninstall wilma
pip3 install ./ --upgrade
```

>NOTE: You need to uninstall first if you already have it installed or pip will use the cached files from the last time you installed it.
