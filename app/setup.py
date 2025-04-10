from setuptools import setup, find_packages

setup(
    name="wilma",
    version="1.1.0",
    description="Simplified CLI Chat Interface for Claude via Amazon Bedrock",
    author="Contributors",
    url="https://github.com/mrgrumpyowl/wilma",
    packages=find_packages(),
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    install_requires=[
        "boto3>=1.28.0",
        "botocore>=1.31.0",
        "prompt_toolkit>=3.0.0",
        "rich>=13.0.0",
        "pathlib>=1.0.0",
        "tiktoken>=0.3.0",
        "halo>=0.0.31",
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "wilma = wilma.main:main",
        ],
    },
    python_requires=">=3.10",
    include_package_data=True,
)
