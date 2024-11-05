# Wilma

# A CLI Chat Interface for Anthropic's Claude LLMs via Amazon Bedrock

A powerful command-line interface for interacting with Anthropic's Claude models through Amazon Bedrock. Wilma provides a feature-rich, user-friendly experience with support for multiline inputs, file analysis, and chat history management.

## Features

- **Multiple Model Support**
  - Claude 3.5 Sonnet (default)
  - Claude 3 Sonnet
  - Claude 3 Haiku

- **Advanced Capabilities**
  - Multiline input support for detailed prompts
  - Real-time streaming responses
  - Supports uploading individual files by entering "Upload: ~/path/to/file_name"
  - Supports uploading an entire directory and its contents recursively by entering "Upload: ~/path/to/directory"
  - Chat history management with conversation resumption
  - Optional web search integration via Perplexity API
  - Markdown-formatted responses
  - Optional user configuration file for setting your preferred default model.

- **Developer-Friendly**
  - Comprehensive error handling
  - AWS authentication management
  - Token count estimation
  - Progress indicators
  - Configurable model parameters

## Prerequisites

- AWS account with Bedrock access
- AWS CLI configured with appropriate credentials
- Perplexity API key for optional web search feature

### Apps and libraries: 
  - Python 3.10 or higher
  - `anthropic` Python package
  - `anthropic[bedrock]` Python package
  - `prompt_toolkit` Python package
  - `rich` Python package
  - `tiktoken` Python package
  - `halo` Python package
  - `tree` command-line utility

## Installation

### Via pip (recommended)

```bash
# Latest version
pip3 install git+https://github.com/mrgrumpyowl/wilma.git@master --upgrade

# Specific version
pip3 install git+https://github.com/mrgrumpyowl/wilma.git@0.2.0 --upgrade
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/mrgrumpyowl/wilma.git
cd wilma

# Install dependencies
pip3 install -r app/requirements.txt

# Ensure the script executable
chmod +x app/wilma.py
```

## Usage

### Basic Usage

```bash
./wilma.py
```

### Command Line Options

```bash
wilma.py [-h] [-m [MODEL]] [-ws] [--debug]

options:
  -h, --help            show this help message and exit
  -m [MODEL], --model-select [MODEL]
                        Select the Anthropic (via Amazon Bedrock) model to use. Options:
                          - Specify a model name directly
                          - Use without a value to select from a list of models available in your authenticated AWS region
                          - Omit to use the default model (claude-3-5-sonnet-20241022)
  -ws, --web-search     Enable web search functionality for answering queries.
  --debug               Enable debug output
```

### Model Selection

By default, wilma will attempt to use the Claude 3.5 Sonnet v2 model. You can:

- Use the `-m` or `--model-select` argument to choose a different model
- Create a config file to set your own default model (see Configuration section below)

If the default model (either system default or your configured default) is not available in your region or you lack permissions to access it, wilma will automatically fall back to showing you a list of available models to choose from.

### Configuration

You can optionally create a configuration file at `~/.wilma/config` to set your preferred default model. The file should contain a line in the following format:

```
default_model = "anthropic.model-name"
```

For example:
```
default_model = "anthropic.claude-3-5-haiku-20240307-v1:0"
```

If the config file doesn't exist or doesn't contain a valid default_model setting, wilma will use its built-in default model.

### File Analysis

```bash
# In the chat interface:
Upload: ~/path/to/file.py    # Analyse single file
Upload: ~/path/to/directory  # Analyse entire directory
```

### Adding to PATH

```bash
sudo ln -s /full/path/to/wilma/app/wilma.py /usr/local/bin/wilma
```

## Configuration

- Chat histories are stored in `~/.wilma/chat-history/`
- AWS credentials should be configured via AWS CLI
- Web search requires `PERPLEXITY_API_KEY` environment variable (optional)

## Development

```bash
# Install in development mode
pip3 uninstall wilma
pip3 install ./ --upgrade

# Run tests (when implemented)
python -m pytest
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m '[tag] Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Versioning

We use [SemVer](http://semver.org/) for versioning. For available versions, see the [tags on this repository](https://github.com/mrgrumpyowl/wilma/tags).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Anthropic for Claude models
- Amazon Web Services for Bedrock
- Wilma generated this, her own README file. 

## Support

For support, please open an issue in the GitHub repository.

---
Built with ❤️ by [Mr. Grumpy Owl](https://github.com/mrgrumpyowl)"
