from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth.deps import SESSION_COOKIE
from app.auth.service import User, pop_flash
from app.order_status import STATUS_LABELS
from app.repositories.cart import cart_count
from app.translations import NAV, PAGES, STATUS_LABELS_EN, STATUS_LABELS_KO

LANG_COOKIE = "dsm_lang"
DEFAULT_LANG = "ko"

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.filters["won"] = lambda value: f"{int(value):,}원"


def _detect_lang(request: Request) -> str:
    lang = request.query_params.get("lang", "")
    if lang in ("ko", "en"):
        return lang
    return request.cookies.get(LANG_COOKIE, DEFAULT_LANG)


def render(
    request: Request,
    conn: object | None,
    template_name: str,
    *,
    user: User | None = None,
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    lang = _detect_lang(request)
    token = request.cookies.get(SESSION_COOKIE)
    flash = pop_flash(conn, token) if conn is not None else None

    # ── bilingual context ────────────────────────────────────────
    page_key = {
        "403.html": "not_authorized",
        "404.html": "not_found",
        "500.html": "server_error",
    }.get(template_name, template_name.replace(".html", ""))

    context["lang"] = lang
    context["lang_toggle"] = ("en" if lang == "ko" else "ko")
    # Preserve query string excluding lang=… when toggling
    qs_parts = []
    for k, vals in request.query_params.items():
        if k != "lang":
            for v in vals:
                qs_parts.append(f"{k}={v}")
    toggle_qs = f"&{'&'.join(qs_parts)}" if qs_parts else ""
    base = str(request.url).split("?")[0]
    context["lang_toggle_url"] = f"{base}?lang={context['lang_toggle']}{toggle_qs}"
    context["lang_toggle_label"] = "EN" if lang == "ko" else "한국어"

    context.setdefault("user", user)
    context["cart_count"] = cart_count(conn, user.id) if conn is not None and user else 0
    context["flash"] = flash
    context.setdefault("status_labels", STATUS_LABELS_KO if lang == "ko" else STATUS_LABELS_EN)

    # Expose page-specific strings
    pages = PAGES.get(lang, PAGES["ko"])
    context["page_title"] = pages.get(page_key, pages.get("home", ""))
    context["msg"] = pages  # shorthand for per-page strings

    # Expose nav strings
    nav = NAV.get(lang, NAV["ko"])
    context["nav"] = nav

    return templates.TemplateResponse(request, template_name, context, status_code=status_code)
