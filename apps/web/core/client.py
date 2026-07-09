"""Cliente HTTP fino da API FastAPI. A UI Django nunca acessa Postgres/Milvus direto."""
from __future__ import annotations

import httpx
from django.conf import settings


class ApiError(Exception):
    def __init__(self, status: int, detail):
        self.status = status
        self.detail = detail
        super().__init__(f"{status}: {detail}")


def _request(method: str, path: str, **kwargs):
    url = settings.API_BASE_URL.rstrip("/") + path
    try:
        resp = httpx.request(method, url, timeout=60, **kwargs)
    except httpx.RequestError as exc:
        raise ApiError(0, f"API indisponível ({exc}).")
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = resp.text or resp.reason_phrase
        raise ApiError(resp.status_code, detail)
    if resp.status_code == 204 or not resp.content:
        return None
    return resp.json()


def get(path: str, params: dict | None = None):
    return _request("GET", path, params=params)


def post(path: str, json: dict | None = None, data: dict | None = None, files=None):
    return _request("POST", path, json=json, data=data, files=files)


def patch(path: str, json: dict | None = None):
    return _request("PATCH", path, json=json)


def delete(path: str):
    return _request("DELETE", path)
