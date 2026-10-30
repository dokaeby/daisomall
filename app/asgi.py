from __future__ import annotations

from app.config import load_settings
from app.main import create_app

app = create_app(load_settings())
