import os
import sys

# Ensure root project directory is in Python's search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
