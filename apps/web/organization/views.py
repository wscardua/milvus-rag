"""Telas de admin: Squads e Processos de Delivery (consomem organization-admin)."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect, render

from core import client


def squads(request):
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "create":
                client.post(
                    "/squads",
                    json={
                        "name": request.POST.get("name", "").strip(),
                        "description": request.POST.get("description") or None,
                    },
                )
                messages.success(request, "Squad criada.")
            elif action == "update":
                client.patch(
                    f"/squads/{request.POST['id']}",
                    json={
                        "name": request.POST.get("name", "").strip(),
                        "description": request.POST.get("description") or None,
                    },
                )
                messages.success(request, "Squad atualizada.")
            elif action == "delete":
                client.delete(f"/squads/{request.POST['id']}")
                messages.success(request, "Squad removida.")
        except client.ApiError as exc:
            messages.error(request, str(exc.detail))
        return redirect("squads")

    try:
        data = client.get("/squads")
    except client.ApiError as exc:
        messages.error(request, str(exc.detail))
        data = []
    return render(request, "organization/squads.html", {"squads": data, "nav": "squads"})


def processes(request):
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "create":
                client.post(
                    "/delivery-processes",
                    json={
                        "squad_id": request.POST["squad_id"],
                        "name": request.POST.get("name", "").strip(),
                        "description": request.POST.get("description") or None,
                    },
                )
                messages.success(request, "Processo criado.")
            elif action == "delete":
                client.delete(f"/delivery-processes/{request.POST['id']}")
                messages.success(request, "Processo removido.")
        except client.ApiError as exc:
            messages.error(request, str(exc.detail))
        return redirect("processes")

    squad_filter = request.GET.get("squad_id") or None
    try:
        squads_list = client.get("/squads")
        params = {"squad_id": squad_filter} if squad_filter else None
        procs = client.get("/delivery-processes", params=params)
    except client.ApiError as exc:
        messages.error(request, str(exc.detail))
        squads_list, procs = [], []
    squad_names = {s["id"]: s["name"] for s in squads_list}
    for p in procs:
        p["squad_name"] = squad_names.get(p["squad_id"], "—")
    return render(
        request,
        "organization/processes.html",
        {"processes": procs, "squads": squads_list, "squad_filter": squad_filter, "nav": "processes"},
    )
