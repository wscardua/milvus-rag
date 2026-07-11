"""Tela de Consulta (consome query-and-citations) + feedback 👍/👎 da resposta."""
from __future__ import annotations

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render

from core import client


def consulta(request):
    squads = categories = doc_types = processes = phases = tags = []
    try:
        squads = client.get("/squads")
        categories = client.get("/categories")
        doc_types = client.get("/doc-types")
        processes = client.get("/delivery-processes")  # ADR-0007, WORK-010 (Fase 1)
        phases = client.get("/delivery-phases")  # ADR-0015 (Fase 2)
        tags = client.get("/tags")  # ADR-0015 (Fase 2)
    except client.ApiError as exc:
        messages.error(request, str(exc.detail))

    result = None
    question = ""
    if request.method == "POST":
        question = request.POST.get("question", "").strip()
        filters = {
            k: request.POST.get(k)
            for k in ("squad", "delivery_process", "category", "doc_type", "delivery_phase")
            if request.POST.get(k)
        }
        selected_tags = request.POST.getlist("tags")  # multi-seleção → OR (ADR-0015)
        if selected_tags:
            filters["tags"] = selected_tags
        payload = {"question": question, "filters": filters or None, "top_k": 5}
        try:
            result = client.post("/query", json=payload)
        except client.ApiError as exc:
            if exc.status == 404:
                messages.info(request, "A consulta ainda não está disponível (endpoint /query não implementado).")
            else:
                messages.error(request, str(exc.detail))

    return render(
        request,
        "query/consulta.html",
        {
            "squads": squads,
            "categories": categories,
            "doc_types": doc_types,
            "processes": processes,
            "phases": phases,
            "tags": tags,
            "result": result,
            "question": question,
            "nav": "consulta",
        },
    )


def query_feedback(request):
    """Proxy do 'joinha' para a API (POST /query/{id}/feedback). Chamado via fetch."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "método inválido"}, status=405)
    query_id = request.POST.get("query_id")
    rating = request.POST.get("rating")
    if not query_id or rating not in ("up", "down"):
        return JsonResponse({"ok": False, "error": "parâmetros inválidos"}, status=400)
    try:
        client.post(f"/query/{query_id}/feedback", json={"rating": rating})
    except client.ApiError as exc:
        return JsonResponse({"ok": False, "error": str(exc.detail)}, status=exc.status or 502)
    return JsonResponse({"ok": True})
