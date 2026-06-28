from __future__ import annotations

from flask import Blueprint, Response, current_app, jsonify, request

from ..config import AppConfig
from ..export import BASE_FIELDS, make_csv, make_xlsx, rows_to_matrix
from ..paperless_client import PaperlessClient, PaperlessError
from ..security import requires_auth
from ..translations import load_translation, SUPPORTED

api_bp = Blueprint("api", __name__)


def client() -> PaperlessClient:
    return PaperlessClient(AppConfig.from_env())


def error_response(exc: Exception, status: int = 400):
    return jsonify({"ok": False, "error": str(exc)}), status


@api_bp.route("/translations/<lang>")
@requires_auth
def translations(lang: str):
    return jsonify(load_translation(lang if lang in SUPPORTED else "nb"))


@api_bp.route("/settings", methods=["GET"])
@requires_auth
def get_settings():
    cfg = AppConfig.from_env()
    return jsonify({
        "base_url": cfg.base_url,
        "has_token": bool(cfg.api_token),
        "default_language": cfg.default_language,
        "basic_auth_enabled": cfg.basic_auth_enabled,
    })


@api_bp.route("/settings", methods=["POST"])
@requires_auth
def post_settings():
    data = request.get_json(silent=True) or {}
    base_url = str(data.get("base_url", "")).strip().rstrip("/")
    api_token = str(data.get("api_token", "")).strip()
    lang = str(data.get("default_language", "nb")).strip() or "nb"
    if not base_url.startswith(("http://", "https://")):
        return error_response(ValueError("URL må starte med http:// eller https://"), 400)
    if not api_token:
        return error_response(ValueError("API-token mangler"), 400)
    cfg = AppConfig.from_env()
    cfg.save_local(base_url, api_token, lang)
    return jsonify({"ok": True})


@api_bp.route("/test")
@requires_auth
def test_connection():
    try:
        return jsonify(client().test_connection())
    except PaperlessError as exc:
        return error_response(exc, 502)


@api_bp.route("/meta")
@requires_auth
def meta():
    try:
        force = request.args.get("force") == "1"
        return jsonify(client().metadata(force=force))
    except PaperlessError as exc:
        return error_response(exc, 502)


@api_bp.route("/documents")
@requires_auth
def documents():
    try:
        page = max(1, int(request.args.get("page", "1")))
        page_size = min(max(1, int(request.args.get("page_size", "25"))), 200)
        args = request.args.to_dict(flat=False)
        return jsonify(client().documents(args, page=page, page_size=page_size))
    except PaperlessError as exc:
        return error_response(exc, 502)
    except ValueError as exc:
        return error_response(exc, 400)


@api_bp.route("/export")
@requires_auth
def export():
    try:
        fmt = request.args.get("format", "csv").lower()
        delimiter = request.args.get("delimiter", ";")
        delimiter = ";" if delimiter not in {",", ";"} else delimiter
        args = request.args.to_dict(flat=False)
        fields = request.args.getlist("fields") or BASE_FIELDS
        fields = [f for f in fields if f in BASE_FIELDS]
        custom_ids = set(request.args.getlist("custom_field_ids"))
        cfg = AppConfig.from_env()
        pl = PaperlessClient(cfg)
        meta = pl.metadata()
        custom_fields = [cf for cf in meta.get("custom_fields", []) if str(cf.get("id")) in custom_ids]
        rows = pl.documents_all(args, max_pages=cfg.max_export_pages)
        matrix = rows_to_matrix(rows, fields, custom_fields)
        if fmt == "xlsx":
            data = make_xlsx(matrix)
            return Response(data, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=paperless_export.xlsx"})
        data = make_csv(matrix, delimiter=delimiter)
        return Response(data, mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=paperless_export.csv"})
    except PaperlessError as exc:
        return error_response(exc, 502)
