#!/usr/bin/env python3

import boto3
import botocore
import json
import os
import random
import time
from typing import Optional, Tuple


def check_aws_authentication() -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check if the user has an active AWS session and get their region.
    Returns a tuple of (is_authenticated, region, error_message)
    """
    try:
        session = boto3.Session()
        credentials = session.get_credentials()

        if not credentials:
            if os.path.exists(os.path.expanduser("~/.aws/credentials")):
                return (
                    False,
                    None,
                    (
                        "No active AWS session found.\n"
                        "Please start a new AWS session using Leapp or saml2aws (etc).\n"
                        "e.g. If using Leapp, run 'leapp session start' to start a new session."
                    ),
                )
            else:
                return (
                    False,
                    None,
                    "No AWS credentials found. Please run 'aws configure' to set up your credentials.",
                )

        region = session.region_name
        if not region:
            return (
                False,
                None,
                "No AWS region configured. Please run 'aws configure' to set up your region.",
            )

        try:
            sts = session.client("sts")
            identity = sts.get_caller_identity()
            return True, region, None

        except botocore.exceptions.ClientError as e:
            if "expired" in str(e).lower():
                return (
                    False,
                    None,
                    (
                        "AWS session has expired.\n"
                        "Please refresh your session using Leapp or saml2aws (etc).\n"
                        "e.g. If using Leapp, run 'leapp session start' to start a new session."
                    ),
                )
            elif "not authorized" in str(e).lower():
                return (
                    False,
                    None,
                    (
                        "Your AWS credentials don't have the required permissions.\n"
                        "Please ensure you have the necessary IAM permissions for Bedrock."
                    ),
                )
            else:
                return False, None, f"AWS authentication error: {str(e)}"

    except botocore.exceptions.ProfileNotFound:
        return (
            False,
            None,
            (
                "AWS profile not found.\n"
                "If using Leapp, ensure you have an active session. "
                "Run 'leapp session start' to start a new session."
            ),
        )
    except botocore.exceptions.NoCredentialsError:
        if os.path.exists(os.path.expanduser("~/.aws/credentials")):
            return (
                False,
                None,
                (
                    "Found AWS credentials but no active session.\n"
                    "Please start a new AWS session using Leapp or saml2aws (etc).\n"
                    "e.g. If using Leapp, run 'leapp session start' to start a new session."
                ),
            )
        else:
            return (
                False,
                None,
                "No AWS credentials found. Please run 'aws configure' to set up your credentials.",
            )


class BedrockClientError(Exception):
    """Base exception class for BedrockClient errors"""

    pass


class MaxRetriesExceeded(BedrockClientError):
    """Raised when max retries are exceeded"""

    pass


class TokenExpiredException(BedrockClientError):
    """Raised when the AWS token has expired"""

    pass


class InferenceProfileRequired(BedrockClientError):
    """Raised when a model requires an inference profile"""

    pass


def refresh_aws_session():
    """
    Force boto3 to create a new session with fresh credentials.
    Returns (success, region_name, error_message)
    """
    try:
        boto3.setup_default_session()  # Clear cached session
        session = boto3.Session()  # Create new session

        # Verify credentials by making an STS call
        sts = session.client("sts")
        sts.get_caller_identity()

        region = session.region_name
        if not region:
            return (
                False,
                None,
                "No AWS region configured. Please run 'aws configure' to set up your region.",
            )

        return True, region, None

    except (
        botocore.exceptions.ClientError,
        botocore.exceptions.NoCredentialsError,
    ) as e:
        error_msg = f"Failed to refresh AWS session: {str(e)}"
        return False, None, error_msg


class BedrockStreamWrapper:
    """Wraps the Bedrock stream response to handle streaming content"""

    def __init__(self, stream_response):
        self.stream = stream_response.get("body")

    def __iter__(self):
        for event in self.stream:
            chunk = json.loads(event["chunk"]["bytes"].decode())
            yield BedrockChunkWrapper(chunk)


class BedrockChunkWrapper:
    """Wraps individual chunks from the stream"""

    def __init__(self, chunk):
        if "type" in chunk:
            self.type = chunk["type"]
        else:
            self.type = "content_block_delta"

        if "delta" in chunk:
            self.delta = BedrockDeltaWrapper(chunk["delta"])
        else:
            content = chunk.get("content", [{"text": ""}])[0]
            self.delta = BedrockDeltaWrapper({"text": content.get("text", "")})


class BedrockDeltaWrapper:
    """Wraps the delta content from chunks"""

    def __init__(self, delta):
        self.text = delta.get("text", "")


class BedrockResponseWrapper:
    """Wraps non-streaming responses"""

    def __init__(self, response):
        content = response.get("content", [{"text": ""}])[0]
        self.content = [BedrockContentWrapper({"text": content.get("text", "")})]


class BedrockContentWrapper:
    """Wraps content from non-streaming responses"""

    def __init__(self, response):
        self.text = response.get("text", "")


class RetryingStreamIterator:
    """Implements retry logic for streaming responses with inference profile support"""

    def __init__(
        self,
        client,
        model_id,
        request_body,
        max_retries=3,
        base_delay=1.0,
        max_delay=20.0,
    ):
        self.client = client
        self.model_id = model_id
        self.request_body = request_body
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.attempt = 0
        self.current_stream = None
        self.current_iterator = None
        self.inference_profile_arn = None

    def _calculate_delay(self) -> float:
        """Calculate delay with exponential backoff and jitter"""
        exp_delay = min(self.max_delay, self.base_delay * (2**self.attempt))
        jitter = random.uniform(0, 0.1 * exp_delay)
        return exp_delay + jitter

    def _get_inference_profile(self):
        """Get inference profile ARN for the model if required"""
        try:
            # First check config file for specific inference profile
            config_path = os.path.expanduser("~/.wilma/config")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    for line in f:
                        if line.strip().startswith("inference_profile"):
                            return line.split("=")[1].strip().strip("\"'")

            # If not in config, try to find from Bedrock
            bedrock = boto3.client("bedrock", region_name=self.client.meta.region_name)
            response = bedrock.list_inference_profiles()
            for profile in response.get("inferenceProfiles", []):
                if self.model_id in profile.get("provisionedModelId", ""):
                    return profile["inferenceProfileArn"]
        except Exception as e:
            # Check if debug is defined in the global scope
            if "debug" in globals() and globals()["debug"]:
                print(f"Error getting inference profile: {e}")
        return None

    def _create_new_stream(self):
        """Create a new stream from the Bedrock client"""
        try:
            kwargs = {
                "modelId": self.model_id,
                "contentType": "application/json",
                "accept": "application/json",
                "body": json.dumps(self.request_body),
            }

            # Add inference profile if needed
            if self.inference_profile_arn is None:
                self.inference_profile_arn = self._get_inference_profile()

            if self.inference_profile_arn:
                # Split the ARN to get just the profile name
                profile_parts = self.inference_profile_arn.split("/")
                if len(profile_parts) > 1:
                    kwargs["modelId"] = profile_parts[-1]
                else:
                    from rich.console import Console

                    console = Console(highlight=False)
                    console.print(
                        "[yellow]Warning: Could not parse inference profile ARN properly[/]"
                    )

            response = self.client.invoke_model_with_response_stream(**kwargs)
            self.current_stream = BedrockStreamWrapper(response)
            self.current_iterator = iter(self.current_stream)
        except botocore.exceptions.ClientError as e:
            if "ExpiredToken" in str(e) or "expired" in str(e).lower():
                raise TokenExpiredException("AWS token has expired")
            if "inference profile" in str(e).lower():
                raise InferenceProfileRequired(
                    f"Model {self.model_id} requires an inference profile"
                )
            raise

    def __iter__(self):
        return self

    def __next__(self):
        while self.attempt <= self.max_retries:
            try:
                if self.current_iterator is None:
                    self._create_new_stream()

                return next(self.current_iterator)

            except StopIteration:
                raise

            except TokenExpiredException:
                raise  # Let the caller handle token expiration

            except InferenceProfileRequired as e:
                from rich.console import Console

                console = Console(highlight=False)
                console.print(f"[red]Error: {str(e)}[/]")
                console.print(
                    "[yellow]Please create an inference profile for this model in AWS Bedrock console.[/]"
                )
                raise

            except (botocore.exceptions.EventStreamError, Exception) as e:
                from rich.console import Console

                console = Console(highlight=False)
                if "serviceunavailableexception" in str(e).lower():
                    if self.attempt < self.max_retries:
                        delay = self._calculate_delay()
                        console.print(
                            f"[yellow]\nService unavailable. Retrying stream in {delay:.2f} seconds (attempt {self.attempt + 1}/{self.max_retries})...\n[/]"
                        )
                        time.sleep(delay)
                        self.attempt += 1
                        self.current_iterator = None  # Force creation of new stream
                        continue
                    else:
                        raise MaxRetriesExceeded(
                            f"Maximum retries ({self.max_retries}) exceeded. Last error: {str(e)}"
                        )
                raise  # Re-raise any other exception


class BedrockClient:
    """Client for interacting with Amazon Bedrock with inference profile support"""

    def __init__(self, region_name=None, max_retries=3, base_delay=1.0, max_delay=20.0):
        try:
            if not region_name:
                session = boto3.Session()
                region_name = session.region_name
                if not region_name:
                    raise RuntimeError("No AWS region configured")

            self.client = boto3.client("bedrock-runtime", region_name=region_name)
            self.bedrock = boto3.client("bedrock", region_name=region_name)
            self.region = region_name
            self.max_retries = max_retries
            self.base_delay = base_delay
            self.max_delay = max_delay
            self._inference_profiles_cache = {}

        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "AccessDeniedException":
                raise RuntimeError("Access denied to Bedrock")
            elif e.response["Error"]["Code"] == "UnrecognizedClientException":
                raise RuntimeError("Invalid AWS credentials")
            else:
                raise RuntimeError(f"Error initializing Bedrock client: {str(e)}")
        except botocore.exceptions.EndpointConnectionError:
            raise RuntimeError(f"Could not connect to Bedrock in region {region_name}")

    def _get_inference_profile(self, model_id: str) -> Optional[str]:
        """Get inference profile ARN for a model, with caching"""
        if model_id not in self._inference_profiles_cache:
            try:
                response = self.bedrock.list_inference_profiles()
                for profile in response.get("inferenceProfiles", []):
                    if model_id in profile.get("provisionedModelId", ""):
                        self._inference_profiles_cache[model_id] = profile[
                            "inferenceProfileArn"
                        ]
                        return profile["inferenceProfileArn"]
                self._inference_profiles_cache[model_id] = None
            except Exception as e:
                # Check if debug is defined in the global scope
                if "debug" in globals() and globals().get("debug"):
                    print(f"Error getting inference profile: {e}")
                self._inference_profiles_cache[model_id] = None

        return self._inference_profiles_cache[model_id]

    def create_message(
        self,
        model_id: str,
        messages: list,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
    ):
        """Create a message with retry logic and inference profile support"""
        # Format messages for Bedrock
        formatted_messages = [
            {"role": msg["role"], "content": [{"type": "text", "text": msg["content"]}]}
            for msg in messages
            if msg.get("content")
        ]

        # Prepare request body
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": formatted_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature or 0.7,
        }
        if system:
            request_body["system"] = system

        if stream:
            return RetryingStreamIterator(
                client=self.client,
                model_id=model_id,
                request_body=request_body,
                max_retries=self.max_retries,
                base_delay=self.base_delay,
                max_delay=self.max_delay,
            )
        else:
            attempt = 0
            while attempt <= self.max_retries:
                try:
                    kwargs = {
                        "modelId": model_id,
                        "contentType": "application/json",
                        "accept": "application/json",
                        "body": json.dumps(request_body),
                    }

                    # Add inference profile if needed
                    profile_arn = self._get_inference_profile(model_id)
                    if profile_arn:
                        kwargs["inferenceProfileArn"] = profile_arn

                    response = self.client.invoke_model(**kwargs)
                    response_body = json.loads(response.get("body").read())
                    return BedrockResponseWrapper(response_body)

                except botocore.exceptions.ClientError as e:
                    if "ExpiredToken" in str(e) or "expired" in str(e).lower():
                        raise TokenExpiredException("AWS token has expired")
                    if "inference profile" in str(e).lower():
                        raise InferenceProfileRequired(
                            f"Model {model_id} requires an inference profile"
                        )
                    if "serviceunavailableexception" in str(e).lower():
                        if attempt < self.max_retries:
                            delay = min(self.max_delay, self.base_delay * (2**attempt))
                            jitter = random.uniform(0, 0.1 * delay)
                            total_delay = delay + jitter
                            print(
                                f"\nService unavailable. Retrying in {total_delay:.2f} seconds (attempt {attempt + 1}/{self.max_retries})..."
                            )
                            time.sleep(total_delay)
                            attempt += 1
                            continue
                        else:
                            raise MaxRetriesExceeded(
                                f"Maximum retries ({self.max_retries}) exceeded. Last error: {str(e)}"
                            )
                    raise

            return None
