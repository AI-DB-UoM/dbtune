from fastapi import HTTPException
from pathlib import Path
import yaml
import requests


def read_configs(options):

    config = {}
    
    if "config_file" in options:
        try:
            with open(Path(options["config_file"])) as f:
                config = yaml.safe_load(f)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read config_file: {e}")
    elif "config_url" in options:
        try:
            r = requests.get(options["config_url"], timeout=5)
            r.raise_for_status()
            config = yaml.safe_load(r.text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch config_url: {e}")

    return config