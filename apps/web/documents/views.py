"""Telas de Documentos: listagem, upload e detalhe (consomem upload-and-metadata + document-links)."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect, render

from core import client


def document_list(request):
    filters = {
        k: request.GET.get(k)
        for k in ("squad_id", "delivery_process_id", "category_id", "doc_type")
        if request.GET.get(k)
    }
    try:
        squads = client.get("/squads")
        categories = client.get("/categories")
        doc_types = client.get("/doc-types")
        processes = client.get("/delivery-processes")
        docs = client.get("/documents", params=filters or None)
    except client.ApiError as exc:
        messages.error(request, str(exc.detail))
        squads, categories, doc_types, processes, docs = [], [], [], [], []

    squad_names = {s["id"]: s["name"] for s in squads}
    cat_names = {c["id"]: c["name"] for c in categories}
    proc_names = {p["id"]: p["name"] for p in processes}
    for d in docs:
        d["squad_name"] = squad_names.get(d.get("squad_id"), "—")
        d["category_name"] = cat_names.get(d.get("category_id"))
        d["process_name"] = proc_names.get(d.get("delivery_process_id"))
    return render(
        request,
        "documents/list.html",
        {
            "documents": docs,
            "squads": squads,
            "categories": categories,
            "doc_types": doc_types,
            "filters": filters,
            "nav": "documentos",
        },
    )


def document_upload(request):
    if request.method == "POST":
        data = {
            "delivery_process_id": request.POST.get("delivery_process_id", ""),
            "author": request.POST.get("author", ""),
            "doc_type": request.POST.get("doc_type", ""),
            "tags": request.POST.get("tags", ""),
        }
        title = request.POST.get("title", "").strip()
        if title:
            data["title"] = title
        data = {k: v for k, v in data.items() if v}
        upload = request.FILES.get("file")
        if not upload:
            messages.error(request, "Selecione um arquivo.")
            return redirect("upload")
        files = {"file": (upload.name, upload.read(), upload.content_type or "application/octet-stream")}
        try:
            doc = client.post("/documents", data=data, files=files)
            messages.success(request, "Documento enviado; ingestão enfileirada.")
            return redirect("document_detail", document_id=doc["id"])
        except client.ApiError as exc:
            messages.error(request, str(exc.detail))
            return redirect("upload")

    try:
        squads = client.get("/squads")
        doc_types = client.get("/doc-types")
        processes = client.get("/delivery-processes")
    except client.ApiError as exc:
        messages.error(request, str(exc.detail))
        squads, doc_types, processes = [], [], []
    procs_by_squad: dict[str, list] = {}
    for p in processes:
        procs_by_squad.setdefault(p["squad_id"], []).append({"id": p["id"], "name": p["name"]})
    return render(
        request,
        "documents/upload.html",
        {
            "squads": squads,
            "doc_types": doc_types,
            "procs_by_squad": procs_by_squad,
            "nav": "upload",
        },
    )


def document_detail(request, document_id):
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "save_classification":
                payload = {
                    "title": request.POST.get("title") or None,
                    "summary": request.POST.get("summary") or None,
                    "category_id": request.POST.get("category_id") or None,
                    "subcategory_id": request.POST.get("subcategory_id") or None,
                }
                client.patch(f"/documents/{document_id}", json=payload)
                messages.success(request, "Classificação salva.")
            elif action == "add_link":
                client.post(
                    f"/documents/{document_id}/links",
                    json={
                        "target_document_id": request.POST["target_document_id"],
                        "link_type": request.POST["link_type"],
                    },
                )
                messages.success(request, "Vínculo adicionado.")
            elif action == "remove_link":
                client.delete(f"/documents/{document_id}/links/{request.POST['link_id']}")
                messages.success(request, "Vínculo removido.")
        except client.ApiError as exc:
            messages.error(request, str(exc.detail))
        return redirect("document_detail", document_id=document_id)

    try:
        doc = client.get(f"/documents/{document_id}")
        links = client.get(f"/documents/{document_id}/links")
        categories = client.get("/categories")
        link_types = client.get("/link-types")
        squads = client.get("/squads")
        processes = client.get("/delivery-processes")
        # subcategorias por categoria (embed p/ select dependente no cliente)
        subcats = {c["id"]: client.get(f"/categories/{c['id']}/subcategories") for c in categories}
        # candidatos a vínculo: documentos da mesma squad (menos ele mesmo)
        same_squad = client.get("/documents", params={"squad_id": doc.get("squad_id")}) if doc.get("squad_id") else []
        candidates = [d for d in same_squad if d["id"] != doc["id"]]
    except client.ApiError as exc:
        messages.error(request, str(exc.detail))
        return redirect("document_list")

    doc["squad_name"] = next((s["name"] for s in squads if s["id"] == doc.get("squad_id")), "—")
    doc["process_name"] = next(
        (p["name"] for p in processes if p["id"] == doc.get("delivery_process_id")), "—"
    )
    for c in candidates:
        c["label"] = c.get("title") or c.get("original_filename") or c["id"]

    doc_titles = {d["id"]: (d.get("title") or d.get("original_filename") or d["id"]) for d in same_squad}
    doc_titles[doc["id"]] = doc.get("title") or doc.get("original_filename") or doc["id"]
    for ln in links:
        ln["source_title"] = doc_titles.get(ln["source_document_id"], ln["source_document_id"])
        ln["target_title"] = doc_titles.get(ln["target_document_id"], ln["target_document_id"])
        ln["outgoing"] = ln["source_document_id"] == doc["id"]

    return render(
        request,
        "documents/detail.html",
        {
            "doc": doc,
            "links": links,
            "categories": categories,
            "subcats": subcats,
            "current_subcats": subcats.get(doc.get("category_id"), []),
            "link_types": link_types,
            "candidates": candidates,
            "nav": "documentos",
        },
    )
