import os

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_URL = os.getenv("MISTRAL_URL", "https://api.mistral.ai/v1")
