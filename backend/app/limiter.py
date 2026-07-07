"""
Shared rate-limiter instance.

Placed in its own module to avoid circular imports between
app.main (which wires the limiter into FastAPI) and
app.routes.* (which decorate individual endpoints with limits).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global limiter — 60 req/min per IP by default.
# Individual routes can override with @limiter.limit("N/period").
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
