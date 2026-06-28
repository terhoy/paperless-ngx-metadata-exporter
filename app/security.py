from __future__ import annotations

from functools import wraps
from hmac import compare_digest
from flask import Response, current_app, request


def requires_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        cfg = current_app.config["APP_CONFIG"]
        if not cfg.basic_auth_enabled:
            return view(*args, **kwargs)
        auth = request.authorization
        ok = bool(
            auth
            and compare_digest(auth.username or "", cfg.basic_auth_user)
            and compare_digest(auth.password or "", cfg.basic_auth_password)
        )
        if not ok:
            return Response(
                "Authentication required",
                401,
                {"WWW-Authenticate": 'Basic realm="Paperless Metadata Exporter"'},
            )
        return view(*args, **kwargs)
    return wrapper
