# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Dates in this file are in format of YYYY-MM-DD (2019-12-13 means 13th of December 2019).

## [[0.2.0]](https://github.com/mrgrumpyowl/wilma/releases/tag/0.2.0) - 2024-11-05

### Added
* Authentication checking and confirmation on program start, along with some more graceful error handling. [@mrgrumpyowl](https://github.com/mrgrumpyowl)
* Dynamic model selection list - only Anthropic models that are actively available to the authenticated user in the current AWS region are listed for selection. [@mrgrumpyowl](https://github.com/mrgrumpyowl)
* Support for a user defined default model in an optional `~/.wilma/config` file. [@mrgrumpyowl](https://github.com/mrgrumpyowl)
* Support for all Anthropic models currently available on Amazon Bedrock. (This is obviously subject to the availability of models in any given AWS region and the user being granted access to those models where available.) [@mrgrumpyowl](https://github.com/mrgrumpyowl)

## [[0.1.0]](https://github.com/mrgrumpyowl/wilma/releases/tag/0.1.0) - 2024-10-28

### Added
* Fully working beta CLI chatbot named `wilma.py`. Leverages Amazon Bedrock via the boto3 library and stored AWS CLI credentials to offer access to Anthropic's Sonnet 3 and Haiku 3 models in a simple chatbot format. I consider this a beta version as the Anthropic models and the AWS region are hard coded in this release. [@mrgrumpyowl](https://github.com/mrgrumpyowl)
