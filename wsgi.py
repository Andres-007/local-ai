"""
WSGI entry for hosts that look for ``wsgi:app`` (e.g. Vercel Python, Gunicorn).

Usage::

    gunicorn wsgi:app
"""
from app import app

__all__ = ["app"]
