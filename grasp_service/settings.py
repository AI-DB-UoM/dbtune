import os


GRASP_MODE = os.getenv("GRASP_MODE", "auto").strip().lower()
GRASP_EXTERNAL_ENDPOINT = os.getenv("GRASP_EXTERNAL_ENDPOINT", "").strip()
GRASP_TIMEOUT_MS = int(os.getenv("GRASP_TIMEOUT_MS", "1500"))
