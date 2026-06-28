from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from ..config import AppConfig
from ..export import BASE_FIELDS, make_csv, make_xlsx, rows_to_matrix
from ..paperless_client import PaperlessClient, PaperlessError
from ..pdf_templates import label_presets, make_content_sheet_pdf, make_label_sheet_pdf, make_combined_archive_pdf
from ..security import requires_auth
from ..translations import SUPPORTED, load_translation

api_bp = Blueprint("api", __name__)


def client() -> PaperlessClient:
    return PaperlessClient(AppConfig.from_env())


def error_response(exc: Exception, status: int = 400):
    return jsonify({"ok": False, "error": str(exc)}), status


def _archive_args() -> tuple[str, str, str, str]:
    return (
        request.args.get("case_id", "").strip(),
        request.args.get("case_title", "").strip(),
        request.args.get("description", "").strip(),
        request.args.get("folder", "1 av 1").strip() or "1 av 1",
    )


@api_bp.route("/translations/<lang>")
@requires_auth
def translations(lang: str):
    return jsonify(load_translation(lang if lang in SUPPORTED else "nb"))


@api_bp.route("/label-presets")
@requires_auth
def get_label_presets():
    return jsonify(label_presets())


@api_bp.route("/settings", methods=["GET"])
@requires_auth
def get_settings():
    cfg = AppConfig.from_env()
    return jsonify({
        "base_url": cfg.base_url,
        "has_token": bool(cfg.api_token),
        "default_language": cfg.default_language,
        "basic_auth_enabled": cfg.basic_auth_enabled,
        "demo_mode": cfg.demo_mode,
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


@api_bp.route("/export/content-sheet")
@requires_auth
def export_content_sheet():
    try:
        cfg = AppConfig.from_env()
        pl = PaperlessClient(cfg)
        rows = pl.documents_all(request.args.to_dict(flat=False), max_pages=cfg.max_export_pages)
        case_id, case_title, description, folder = _archive_args()
        pdf = make_content_sheet_pdf(rows, case_id=case_id, case_title=case_title, description=description, folder=folder)
        filename = f"{case_id or 'arkiv'}_innholdsark.pdf"
        return Response(pdf, mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})
    except PaperlessError as exc:
        return error_response(exc, 502)


@api_bp.route("/export/label-sheet")
@requires_auth
def export_label_sheet():
    try:
        cfg = AppConfig.from_env()
        pl = PaperlessClient(cfg)
        rows = pl.documents_all(request.args.to_dict(flat=False), max_pages=cfg.max_export_pages)
        case_id, case_title, _description, folder = _archive_args()
        preset_name = request.args.get("label_preset", "avery_l4745rev_25")
        try:
            x_offset_mm = float(request.args.get("x_offset_mm", "0") or 0)
            y_offset_mm = float(request.args.get("y_offset_mm", "0") or 0)
        except ValueError:
            x_offset_mm = 0.0
            y_offset_mm = 0.0
        pdf = make_label_sheet_pdf(
            rows,
            case_id=case_id,
            case_title=case_title,
            folder=folder,
            preset_name=preset_name,
            x_offset_mm=x_offset_mm,
            y_offset_mm=y_offset_mm,
        )
        filename = f"{case_id or 'arkiv'}_etiketter.pdf"
        return Response(pdf, mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})
    except PaperlessError as exc:
        return error_response(exc, 502)


@api_bp.route("/export/archive-pdf")
@requires_auth
def export_archive_pdf():
    try:
        cfg = AppConfig.from_env()
        pl = PaperlessClient(cfg)
        rows = pl.documents_all(request.args.to_dict(flat=False), max_pages=cfg.max_export_pages)
        case_id, case_title, description, folder = _archive_args()
        pdf = make_combined_archive_pdf(rows, case_id=case_id, case_title=case_title, description=description, folder=folder)
        filename = f"{case_id or 'arkiv'}_arkivpakke.pdf"
        return Response(pdf, mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})
    except PaperlessError as exc:
        return error_response(exc, 502)
