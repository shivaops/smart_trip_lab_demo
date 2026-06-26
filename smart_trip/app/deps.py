# app/deps.py
"""
Shared app dependencies (Jinja templates).

Why:
- Avoid creating Jinja2Templates in every router file.
- Keep templates directory in one place.
"""

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
