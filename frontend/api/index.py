import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from mangum import Mangum
from main import app

# Mangum wraps FastAPI for AWS Lambda / Vercel serverless.
# Strip /api prefix so FastAPI routes match.
handler = Mangum(app, api_gateway_base_path="/api")