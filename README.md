# Wilma

# A CLI Chat Interface for Claude Models via AWS Bedrock

A powerful command-line interface for interacting with Anthropic's Claude models through Amazon Bedrock. Wilma provides a feature-rich, user-friendly experience with support for multiline inputs, file analysis, and chat history management.

## Features

- **Multiple Model Support**
  - Claude 3.5 Sonnet (default)
  - Claude 3 Sonnet
  - Claude 3 Haiku

- **Advanced Capabilities**
  - Multiline input support for detailed prompts
  - Real-time streaming responses
  - File and directory analysis (`Upload: ~/path/to/file`)
  - Chat history management with conversation resumption
  - Optional web search integration via Perplexity API
  - Markdown-formatted responses

- **Developer-Friendly**
  - Comprehensive error handling
  - AWS authentication management
  - Token count estimation
  - Progress indicators
  - Configurable model parameters

## Prerequisites

- Python 3.10 or higher
- AWS account with Bedrock access
- AWS CLI configured with appropriate credentials
- `tree` command-line utility
- Perplexity API key for optional web search feature

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
./wilma.py [-h] [-m [MODEL]] [-ws]

options:
  -h, --help            show help message
  -m [MODEL], --model-select [MODEL]
                        Select AI model or show model menu
  -ws, --web-search     Enable web search functionality
  ```

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
