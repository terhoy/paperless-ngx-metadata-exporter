from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any
from urllib.parse import urljoin

import requests

from .config import AppConfig


class PaperlessError(RuntimeError):
    pass


@dataclass
class MetadataCache:
    data: dict[str, Any]
    fetched_at: float = 0.0


META_CACHE = MetadataCache(data={
    "correspondents": [],
    "document_types": [],
    "tags": [],
    "storage_paths": [],
    "custom_fields": [],
})


class PaperlessClient:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.base_url = cfg.base_url.rstrip("/")
        self.timeout = cfg.request_timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Token {self.cfg.api_token}"}

    def _api_url(self, path: str) -> str:
        return urljoin(self.base_url + "/", "api/" + path.lstrip("/"))

    def configured(self) -> bool:
        return bool(self.base_url and self.cfg.api_token)

    def validate_config(self) -> None:
        if not self.base_url.startswith(("http://", "https://")):
            raise PaperlessError("Ugyldig URL. URL må starte med http:// eller https://")
        if not self.cfg.api_token:
            raise PaperlessError("API-token mangler")

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        self.validate_config()
        try:
            r = requests.request(
                method,
                self._api_url(path),
                headers=self._headers(),
                timeout=self.timeout,
                **kwargs,
            )
        except requests.exceptions.Timeout as exc:
            raise PaperlessError("Timeout mot Paperless-ngx") from exc
        except requests.exceptions.ConnectionError as exc:
            raise PaperlessError("Kunne ikke koble til Paperless-ngx") from exc

        if r.status_code == 401:
            raise PaperlessError("Ugyldig API-token eller manglende tilgang")
        if r.status_code >= 400:
            raise PaperlessError(f"Paperless-ngx svarte med HTTP {r.status_code}")
        return r

    def test_connection(self) -> dict[str, Any]:
        r = self.request("GET", "documents/?page_size=1")
        data = r.json()
        return {"ok": True, "document_count": data.get("count", 0)}

    def _fetch_all_simple(self, endpoint: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        page = 1
        while True:
            r = self.request("GET", f"{endpoint}/", params={"page_size": 1000, "page": page})
            data = r.json()
            results.extend(data.get("results", []))
            if not data.get("next"):
                break
            page += 1
            if page > 100:
                break
        return results

    def metadata(self, force: bool = False) -> dict[str, Any]:
        now = time.time()
        if not force and META_CACHE.fetched_at and now - META_CACHE.fetched_at < self.cfg.metadata_ttl_seconds:
            return META_CACHE.data
        data = {
            "correspondents": self._fetch_all_simple("correspondents"),
            "document_types": self._fetch_all_simple("document_types"),
            "tags": self._fetch_all_simple("tags"),
            "storage_paths": self._fetch_all_simple("storage_paths"),
            "custom_fields": [],
        }
        try:
            data["custom_fields"] = self._fetch_all_simple("custom_fields")
        except PaperlessError:
            data["custom_fields"] = []
        META_CACHE.data = data
        META_CACHE.fetched_at = now
        return data

    @staticmethod
    def _name_by_id(items: list[dict[str, Any]]) -> dict[Any, str]:
        return {i.get("id"): i.get("name", "") for i in items}

    def _normalize_custom_fields(self, doc: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
        field_names = self._name_by_id(meta.get("custom_fields", []))
        out: dict[str, Any] = {}
        for cf in doc.get("custom_fields", []) or []:
            field_id = cf.get("field") or cf.get("id") or cf.get("custom_field")
            name = field_names.get(field_id) or cf.get("name") or str(field_id or "unknown")
            out[str(field_id or name)] = {"id": field_id, "name": name, "value": cf.get("value")}
        return out

    def normalize_document(self, doc: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
        correspondents = self._name_by_id(meta.get("correspondents", []))
        document_types = self._name_by_id(meta.get("document_types", []))
        tags = self._name_by_id(meta.get("tags", []))
        storage_paths = self._name_by_id(meta.get("storage_paths", []))
        doc_id = doc.get("id")
        return {
            "id": doc_id,
            "created": (doc.get("created") or "").split("T")[0],
            "added": (doc.get("added") or "").split("T")[0],
            "title": doc.get("title") or "",
            "correspondent": correspondents.get(doc.get("correspondent"), ""),
            "document_type": document_types.get(doc.get("document_type"), ""),
            "tags": ", ".join(tags.get(t, "") for t in doc.get("tags", []) if tags.get(t, "")),
            "storage_path": storage_paths.get(doc.get("storage_path"), ""),
            "custom_fields": self._normalize_custom_fields(doc, meta),
            "link": f"{self.base_url}/documents/{doc_id}" if doc_id else "",
        }

    def document_query_params(self, args: dict[str, list[str]]) -> list[tuple[str, str]]:
        allowed = {
            "query",
            "correspondent__id", "correspondent__isnull",
            "document_type__id", "document_type__isnull",
            "storage_path__id", "storage_path__isnull",
            "tags__id__all", "is_tagged",
            "created__date__gte", "created__date__lte",
            "added__date__gte", "added__date__lte",
        }
        out: list[tuple[str, str]] = []
        for k, values in args.items():
            if k not in allowed:
                continue
            for value in values:
                value = str(value).strip()
                if value:
                    out.append((k, value))
        return out

    def documents(self, args: dict[str, list[str]], page: int = 1, page_size: int = 25) -> dict[str, Any]:
        meta = self.metadata()
        params = self.document_query_params(args)
        params.extend([("page", str(page)), ("page_size", str(page_size))])
        r = self.request("GET", "documents/", params=params)
        data = r.json()
        return {
            "count": data.get("count", 0),
            "page": page,
            "page_size": page_size,
            "results": [self.normalize_document(d, meta) for d in data.get("results", [])],
        }

    def documents_all(self, args: dict[str, list[str]], page_size: int = 100, max_pages: int = 200) -> list[dict[str, Any]]:
        all_rows: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            batch = self.documents(args, page=page, page_size=page_size)
            all_rows.extend(batch["results"])
            if page * page_size >= int(batch.get("count") or 0):
                break
        return all_rows
