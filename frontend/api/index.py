import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from main import app

# Vercel Python runtime: expose an ASGI app directly.
# Strip /api prefix so FastAPI routes match.
async def handler(scope, receive, send):
    if scope["type"] == "http" and scope["path"].startswith("/api"):
        scope["path"] = scope["path"][4:]  # strip "/api"
        if scope.get("root_path", "").startswith("/api"):
            scope["root_path"] = scope["root_path"][4:]
    return await app(scope, receive, send)