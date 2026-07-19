import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/config", tags=["config"])

class ConfigSaveRequest(BaseModel):
    MISTRAL_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    GITHUB_TOKEN: str = ""

MASK = "••••••••"

@router.get("")
async def get_config() -> dict[str, str]:
    """Retrieve the current configuration keys, masked for security."""
    config_keys = [
        "MISTRAL_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "GITHUB_TOKEN",
    ]
    
    response = {}
    for key in config_keys:
        # Check settings. This dynamically checks the local file or falls back to env
        val = getattr(settings, key.lower(), "")
        response[key] = MASK if val else ""
        
    return response

@router.post("")
async def save_config(payload: ConfigSaveRequest) -> dict[str, str]:
    """Save updated configurations to the local shared volume."""
    shared_dir = Path(settings.repos_base_path)
    # Ensure directory exists
    shared_dir.mkdir(parents=True, exist_ok=True)
    local_settings_file = shared_dir / "local_settings.json"
    
    current_data = {}
    if local_settings_file.exists():
        try:
            with open(local_settings_file) as f:
                current_data = json.load(f)
        except Exception:
            pass
            
    payload_dict = payload.model_dump()
    for key, value in payload_dict.items():
        value = value.strip()
        if value == MASK:
            # Mask placeholder sent: do not overwrite current configured value
            continue
        elif value == "":
            # Empty string sent: delete this key from the local config
            if key in current_data:
                del current_data[key]
        else:
            # New value sent: save it
            current_data[key] = value
            
    try:
        with open(local_settings_file, "w") as f:
            json.dump(current_data, f, indent=2)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write configuration file: {e}"
        )
        
    return {"status": "success", "message": "Configuration saved successfully"}
