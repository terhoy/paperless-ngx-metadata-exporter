from __future__ import annotations

from typing import Any

DEMO_META: dict[str, list[dict[str, Any]]] = {
    "correspondents": [
        {"id": 1, "name": "Altifiber"},
        {"id": 2, "name": "Telenor"},
        {"id": 3, "name": "Entreprenør AS"},
        {"id": 4, "name": "Internt"},
    ],
    "document_types": [
        {"id": 1, "name": "Avtale"},
        {"id": 2, "name": "E-post"},
        {"id": 3, "name": "Tegning"},
        {"id": 4, "name": "Referat"},
        {"id": 5, "name": "Kontroll"},
    ],
    "tags": [
        {"id": 1, "name": "Uleberg"},
        {"id": 2, "name": "Fiber"},
        {"id": 3, "name": "Arkivmappe"},
    ],
    "storage_paths": [
        {"id": 1, "name": "Prosjekt/Uleberg"},
    ],
    "custom_fields": [
        {"id": 101, "name": "Saks-ID", "data_type": "string"},
        {"id": 102, "name": "Sakstittel", "data_type": "string"},
        {"id": 103, "name": "Mappe", "data_type": "string"},
    ],
}

DEMO_DOCS: list[dict[str, Any]] = [
    {"id": 1, "created": "2024-02-15", "added": "2024-02-16", "title": "Avtale med Altifiber - etablering og leveranse", "correspondent": "Altifiber", "document_type": "Avtale", "tags": "Uleberg, Fiber", "storage_path": "Prosjekt/Uleberg", "link": "#", "custom_fields": {"101": {"id": 101, "name": "Saks-ID", "value": "VF-2026-0123"}, "102": {"id": 102, "name": "Sakstittel", "value": "Uleberg fiber"}, "103": {"id": 103, "name": "Mappe", "value": "1/1"}}},
    {"id": 2, "created": "2024-03-01", "added": "2024-03-02", "title": "Telenor - avklaring av termineringspunkt", "correspondent": "Telenor", "document_type": "E-post", "tags": "Uleberg, Fiber", "storage_path": "Prosjekt/Uleberg", "link": "#", "custom_fields": {"101": {"id": 101, "name": "Saks-ID", "value": "VF-2026-0123"}, "102": {"id": 102, "name": "Sakstittel", "value": "Uleberg fiber"}, "103": {"id": 103, "name": "Mappe", "value": "1/1"}}},
    {"id": 3, "created": "2024-04-12", "added": "2024-04-13", "title": "Trasekart og foreløpig føringsvei Uleberg", "correspondent": "Entreprenør AS", "document_type": "Tegning", "tags": "Uleberg, Fiber", "storage_path": "Prosjekt/Uleberg", "link": "#", "custom_fields": {"101": {"id": 101, "name": "Saks-ID", "value": "VF-2026-0123"}, "102": {"id": 102, "name": "Sakstittel", "value": "Uleberg fiber"}, "103": {"id": 103, "name": "Mappe", "value": "1/1"}}},
    {"id": 4, "created": "2024-05-20", "added": "2024-05-21", "title": "Møtereferat prosjektstatus og videre oppfølging", "correspondent": "Internt", "document_type": "Referat", "tags": "Uleberg, Arkivmappe", "storage_path": "Prosjekt/Uleberg", "link": "#", "custom_fields": {"101": {"id": 101, "name": "Saks-ID", "value": "VF-2026-0123"}, "102": {"id": 102, "name": "Sakstittel", "value": "Uleberg fiber"}, "103": {"id": 103, "name": "Mappe", "value": "1/1"}}},
    {"id": 5, "created": "2026-06-28", "added": "2026-06-28", "title": "Arkivkontroll og metadataeksport", "correspondent": "Internt", "document_type": "Kontroll", "tags": "Uleberg, Arkivmappe", "storage_path": "Prosjekt/Uleberg", "link": "#", "custom_fields": {"101": {"id": 101, "name": "Saks-ID", "value": "VF-2026-0123"}, "102": {"id": 102, "name": "Sakstittel", "value": "Uleberg fiber"}, "103": {"id": 103, "name": "Mappe", "value": "1/1"}}},
]


def demo_documents(page: int = 1, page_size: int = 25) -> dict[str, Any]:
    start = (page - 1) * page_size
    end = start + page_size
    return {"count": len(DEMO_DOCS), "page": page, "page_size": page_size, "results": DEMO_DOCS[start:end]}
