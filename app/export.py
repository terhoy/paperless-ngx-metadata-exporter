from __future__ import annotations

from io import BytesIO, StringIO
import csv
from typing import Any

from openpyxl import Workbook

BASE_FIELDS = [
    "created", "added", "title", "correspondent", "document_type", "tags", "storage_path", "link"
]

FIELD_LABELS_NB = {
    "created": "Dokumentdato",
    "added": "Lagt til",
    "title": "Tittel",
    "correspondent": "Korrespondent",
    "document_type": "Dokumenttype",
    "tags": "Tagger",
    "storage_path": "Lagringssti",
    "link": "Lenke",
}


def _custom_value(row: dict[str, Any], custom_id: str) -> Any:
    cf = (row.get("custom_fields") or {}).get(str(custom_id))
    return "" if not cf else cf.get("value", "")


def rows_to_matrix(rows: list[dict[str, Any]], fields: list[str], custom_fields: list[dict[str, Any]]) -> list[list[Any]]:
    headers = [FIELD_LABELS_NB.get(f, f) for f in fields]
    headers += [cf.get("name") or str(cf.get("id")) for cf in custom_fields]
    matrix = [headers]
    for row in rows:
        line = [row.get(f, "") for f in fields]
        line += [_custom_value(row, str(cf.get("id"))) for cf in custom_fields]
        matrix.append(line)
    return matrix


def make_csv(matrix: list[list[Any]], delimiter: str = ";") -> bytes:
    sio = StringIO()
    writer = csv.writer(sio, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
    writer.writerows(matrix)
    return ("﻿" + sio.getvalue()).encode("utf-8")


def make_xlsx(matrix: list[list[Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Export"
    for row in matrix:
        ws.append(row)
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)
    bio = BytesIO()
    wb.save(bio)
    return bio.getvalue()
