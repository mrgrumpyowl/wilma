MODEL_CONFIG = {
    "anthropic.claude-3-sonnet-20240229-v1:0": {
        "friendly_name": "Claude 3 Sonnet (Bedrock)",
        "max_tokens": 8192,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
    },
    "anthropic.claude-3-haiku-20240307-v1:0": {
        "friendly_name": "Claude 3 Haiku (Bedrock)",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "bedrock",
        "supports_system_message": True,
        "supports_streaming": True,
    },
}

def get_model_list():
    return list(MODEL_CONFIG.keys())

def get_model_config(model_name):
    return MODEL_CONFIG.get(model_name)
