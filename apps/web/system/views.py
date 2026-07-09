"""Tela de Logs & Saúde (consome logs-and-health: GET /health e GET /logs)."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import render

from core import client

LEVELS = ("INFO", "WARN", "ERROR")
COMPONENTS = ("api", "worker", "ingestion", "retrieval")


def logs(request):
    filters = {
        k: request.GET.get(k)
        for k in ("level", "component")
        if request.GET.get(k)
    }
    health = None
    log_rows = []
    try:
        health = client.get("/health")
    except client.ApiError as exc:
        messages.error(request, f"Não foi possível obter a saúde dos serviços: {exc.detail}")
    try:
        log_rows = client.get("/logs", params={**filters, "limit": 200}) or []
    except client.ApiError as exc:
        messages.error(request, f"Não foi possível carregar os logs: {exc.detail}")

    return render(
        request,
        "system/logs.html",
        {
            "health": health,
            "logs": log_rows,
            "levels": LEVELS,
            "components": COMPONENTS,
            "filters": filters,
            "nav": "logs",
        },
    )
