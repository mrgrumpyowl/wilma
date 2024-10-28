# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Dates in this file are in format of YYYY-MM-DD (2019-12-13 means 13th of December 2019).


## [[0.1.0]](https://github.com/mrgrumpyowl/wilma/releases/tag/0.1.0) - 2024-10-28

### Added
* Fully working beta CLI chatbot named `wilma.py`. Leverages Amazon Bedrock via the boto3 library and stored AWS CLI credentials to offer access to Anthropic's Sonnet 3 and Haiku 3 models in a simple chatbot format. I consider this a beta version as the Anthropic models and the AWS region are hard coded in this release. [@mrgrumpyowl](https://github.com/mrgrumpyowl)
