MODEL_CONFIG = {
    "claude-3-5-sonnet-20241022": {
        "friendly_name": "Claude 3.5 Sonnet",
        "max_tokens": 8192,
        "temperature": 0.5,
        "provider": "anthropic",
        "supports_system_message": False,
        "supports_streaming": True,
    },
    "claude-3-opus-20240229": {
        "friendly_name": "Claude 3 Opus",
        "max_tokens": 4096,
        "temperature": 0.5,
        "provider": "anthropic",
        "supports_system_message": False,
        "supports_streaming": True,
    },
}

def get_model_list():
    return list(MODEL_CONFIG.keys())

def get_model_config(model_name):
    return MODEL_CONFIG.get(model_name)
