from contextvars import ContextVar
from typing import Any

# Each endpoint establishes and clears this context, including cached client misses.
oauth_request: ContextVar[dict[str, Any]] = ContextVar('oauth_request')
