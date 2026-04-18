"""
AlphaFX root conftest.py
Ensures the code/backend directory is on sys.path and Django is configured
when pytest is invoked from the project root directory.
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR  = PROJECT_ROOT / "code" / "backend"

# Add backend to path so alphafx package and apps are importable
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Set Django settings before any test module is imported
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alphafx.settings.base")

import django
from django.conf import settings

if not settings.configured:
    django.setup()
