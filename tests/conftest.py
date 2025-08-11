import os
import sys


# Ensure project root is on sys.path so tests can import `main` and `models`
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Provide a harmless default API key for OpenAI so importing modules
# that instantiate the client doesn't fail in CI.
os.environ.setdefault("OPENAI_API_KEY", "test")
