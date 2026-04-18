"""
AlphaFX Backend - pytest configuration
Configures Django settings before any test collection begins.
This ensures tests work whether pytest is run from:
  - code/backend/         (direct)
  - project root          (via testpaths)
  - any subdirectory
"""

import os
import sys
from pathlib import Path

# Resolve the backend directory regardless of where pytest is invoked from
BACKEND_DIR = Path(__file__).resolve().parent

# Add backend dir to sys.path so Django can find the alphafx package
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Set Django settings module before anything else imports Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alphafx.settings.base")

# Configure Django immediately so imports in test files work at collection time
import django
from django.conf import settings

if not settings.configured:
    django.setup()
