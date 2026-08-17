"""Environment/config loading. Fails fast with a human-readable error rather
than letting a missing key surface as a raw stack trace deep in an API call."""
import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))


def require_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it "
            "in, or run `export ANTHROPIC_API_KEY=<your-key>` before starting the app."
        )
    return key
