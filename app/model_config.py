import boto3
import botocore
import json

MODEL_CONFIG = {
    # Claude 3.7 Sonnet configurations
    "anthropic.claude-3-7-sonnet-20250219-v1:0": {
        "friendly_name": "Claude 3.7 Sonnet (Bedrock)",
        "max_tokens": 8192,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "Feb 2025",
    },
    # Claude 3.5 Haiku configuration
    "anthropic.claude-3-5-haiku-20241022-v1:0": {
        "friendly_name": "Claude 3.5 Haiku (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "July 2024",
    },
    # Claude 3.5 Sonnet v2 configurations
    "anthropic.claude-3-5-sonnet-20241022-v2:0": {
        "friendly_name": "Claude 3.5 Sonnet v2 (Bedrock)",
        "max_tokens": 8192,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "April 2024",
    },
    # Claude 3.5 Sonnet configurations
    "anthropic.claude-3-5-sonnet-20240620-v1:0:18k": {
        "friendly_name": "Claude 3.5 Sonnet 18K (June 2024)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "April 2024",
    },
    "anthropic.claude-3-5-sonnet-20240620-v1:0:51k": {
        "friendly_name": "Claude 3.5 Sonnet 51K (June 2024)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "April 2024",
    },
    "anthropic.claude-3-5-sonnet-20240620-v1:0:200k": {
        "friendly_name": "Claude 3.5 Sonnet 200K (June 2024)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "April 2024",
    },
    "anthropic.claude-3-5-sonnet-20240620-v1:0": {
        "friendly_name": "Claude 3.5 Sonnet (June 2024)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "April 2024",
    },
    # Claude 3 Haiku configurations
    "anthropic.claude-3-haiku-20240307-v1:0": {
        "friendly_name": "Claude 3 Haiku (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    "anthropic.claude-3-haiku-20240307-v1:0:48k": {
        "friendly_name": "Claude 3 Haiku 48K (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    "anthropic.claude-3-haiku-20240307-v1:0:200k": {
        "friendly_name": "Claude 3 Haiku 200K (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    # Claude 3 Sonnet configurations
    "anthropic.claude-3-sonnet-20240229-v1:0": {
        "friendly_name": "Claude 3 Sonnet (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    "anthropic.claude-3-sonnet-20240229-v1:0:28k": {
        "friendly_name": "Claude 3 Sonnet 28K (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    "anthropic.claude-3-sonnet-20240229-v1:0:200k": {
        "friendly_name": "Claude 3 Sonnet 200K (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    # Claude 3 Opus configurations
    "anthropic.claude-3-opus-20240229-v1:0:12k": {
        "friendly_name": "Claude 3 Opus 12K (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    "anthropic.claude-3-opus-20240229-v1:0:28k": {
        "friendly_name": "Claude 3 Opus 28K (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    "anthropic.claude-3-opus-20240229-v1:0:200k": {
        "friendly_name": "Claude 3 Opus 200K (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    "anthropic.claude-3-opus-20240229-v1:0": {
        "friendly_name": "Claude 3 Opus (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    # Claude v2 configurations
    "anthropic.claude-v2:0:18k": {
        "friendly_name": "Claude 2.0 18K (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    "anthropic.claude-v2:0:100k": {
        "friendly_name": "Claude 2.0 100K (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    "anthropic.claude-v2:1:18k": {
        "friendly_name": "Claude 2.1 18K (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    "anthropic.claude-v2:1:200k": {
        "friendly_name": "Claude 2.1 200K (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    "anthropic.claude-v2:1": {
        "friendly_name": "Claude 2.1 (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    "anthropic.claude-v2": {
        "friendly_name": "Claude 2 (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    # Claude Instant configurations
    "anthropic.claude-instant-v1:2:100k": {
        "friendly_name": "Claude Instant 100K (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
    "anthropic.claude-instant-v1": {
        "friendly_name": "Claude Instant (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
        "training_cutoff": "August 2023",
    },
}


def check_model_access(runtime_client, model_id, debug=False):
    """
    Check if we have access to a specific model by attempting to invoke it.
    Returns True if we have access, False otherwise.
    """
    try:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "test"}]}
            ],
            "max_tokens": 1,
            "temperature": 0,
        }

        runtime_client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body),
        )
        return True
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        error_message = str(e)

        if error_code == "AccessDeniedException":
            if debug:
                print(f"Note: Model {model_id} is available but access is not granted")
            return False
        elif "inference profile" in error_message.lower():
            if debug:
                print(f"Note: Model {model_id} requires an inference profile")
            return True  # Model exists but needs profile configuration
        # For any other error, we'll log it but assume we don't have access
        if debug:
            print(f"Warning: Unexpected error checking access for {model_id}: {e}")
        return False


def get_available_models(region_name=None, debug=False):
    """
    Get list of available Anthropic models in the current AWS region.
    Returns a filtered list of models that are both available and accessible.
    """
    try:
        if not region_name:
            session = boto3.Session()
            region_name = session.region_name

        bedrock = boto3.client("bedrock", region_name=region_name)
        runtime_client = boto3.client("bedrock-runtime", region_name=region_name)

        response = bedrock.list_foundation_models(byProvider="anthropic")

        available_models = [model["modelId"] for model in response["modelSummaries"]]

        # Filter models that are both available, configured, and accessible
        configured_models = []
        for model_id in available_models:
            if model_id in MODEL_CONFIG:
                if check_model_access(runtime_client, model_id, debug):
                    configured_models.append(model_id)
            else:
                if debug:
                    print(
                        f"Warning: Found available model {model_id} but no configuration exists"
                    )

        return configured_models

    except Exception as e:
        error_msg = f"Error fetching available models: {e}"
        if debug:
            print(error_msg)
        return []


def get_model_list():
    """
    This function is maintained for backward compatibility
    but now returns only available models rather than all configured models
    """
    return get_available_models()


def get_model_config(model_name):
    return MODEL_CONFIG.get(model_name)
