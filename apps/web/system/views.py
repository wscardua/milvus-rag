"""Tela de Logs & Saúde (consome logs-and-health: GET /health e GET /logs)."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import render

from core import client

LEVELS = ("INFO", "WARN", "ERROR")
COMPONENTS = ("api", "worker", "ingestion", "retrieval")
PAGE_SIZE = 100  # eventos por página (paginação — WORK-007)


def logs(request):
    filters = {
        k: request.GET.get(k)
        for k in ("level", "component")
        if request.GET.get(k)
    }
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        page = 1
    health = None
    log_rows, total = [], 0
    try:
        health = client.get("/health")
    except client.ApiError as exc:
        messages.error(request, f"Não foi possível obter a saúde dos serviços: {exc.detail}")
    try:
        log_rows, total = client.get_paginated(
            "/logs", params={**filters, "limit": PAGE_SIZE, "offset": (page - 1) * PAGE_SIZE}
        )
    except client.ApiError as exc:
        messages.error(request, f"Não foi possível carregar os logs: {exc.detail}")

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    querystring = request.GET.copy()
    querystring.pop("page", None)
    return render(
        request,
        "system/logs.html",
        {
            "health": health,
            "logs": log_rows,
            "levels": LEVELS,
            "components": COMPONENTS,
            "filters": filters,
            "page": page,
            "total": total,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "base_qs": querystring.urlencode(),
            "nav": "logs",
        },
    )
