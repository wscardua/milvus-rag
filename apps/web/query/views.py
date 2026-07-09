"""Tela de Consulta (consome query-and-citations). Shell tolerante enquanto /query não existe."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import render

from core import client


def consulta(request):
    squads = categories = doc_types = []
    try:
        squads = client.get("/squads")
        categories = client.get("/categories")
        doc_types = client.get("/doc-types")
    except client.ApiError as exc:
        messages.error(request, str(exc.detail))

    result = None
    question = ""
    if request.method == "POST":
        question = request.POST.get("question", "").strip()
        filters = {
            k: request.POST.get(k)
            for k in ("squad", "delivery_process", "category", "doc_type")
            if request.POST.get(k)
        }
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
            "result": result,
            "question": question,
            "nav": "consulta",
        },
    )
