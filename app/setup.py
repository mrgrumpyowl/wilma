"""
Setup.

Package Setup.
"""

from setuptools import find_packages
from setuptools import setup

print("Detected Packages:", find_packages())

setup(
    name="wilma",
    version="0.1.0",
    description="An Anthropic Claude chatbot that uses Amazon Bedrock",
    author="Contributors",
    url=("https://github.com/mrgrumpyowl/ai-tools.git"),
    py_modules=["wilma", "model_config"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    install_requires=[
      "requests",
      "tiktoken",
      "anthropic",
      "prompt_toolkit",
      "rich",
      "boto3",
    ],
    entry_points={
        "console_scripts": [
            "chatbot = chatbot:main",
        ],
    },
)
