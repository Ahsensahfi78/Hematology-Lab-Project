import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from mangum import Mangum
from main import app

handler = Mangum(app)