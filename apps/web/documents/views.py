"""Telas de Documentos: listagem, upload e detalhe (consomem upload-and-metadata + document-links)."""
from __future__ import annotations

import httpx
from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

from core import client

# Formatos que o navegador renderiza inline no modal; o resto é só download (ADR-0010).
PREVIEWABLE_EXTS = ("pdf", "txt", "md", "html", "htm")


PAGE_SIZE = 20  # itens por página na listagem (paginação — WORK-007)


def document_list(request):
    filters = {
        k: request.GET.get(k)
        for k in ("squad_id", "delivery_process_id", "delivery_phase", "category_id", "doc_type")
        if request.GET.get(k)
    }
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        page = 1
    params = {**filters, "limit": PAGE_SIZE, "offset": (page - 1) * PAGE_SIZE}
    try:
        squads = client.get("/squads")
        categories = client.get("/categories")
        doc_types = client.get("/doc-types")
        phases = client.get("/delivery-phases")
        processes = client.get("/delivery-processes")
        docs, total = client.get_paginated("/documents", params=params)
    except client.ApiError as exc:
        messages.error(request, str(exc.detail))
        squads, categories, doc_types, phases, processes, docs, total = [], [], [], [], [], [], 0

    squad_names = {s["id"]: s["name"] for s in squads}
    cat_names = {c["id"]: c["name"] for c in categories}
    proc_names = {p["id"]: p["name"] for p in processes}
    for d in docs:
        d["squad_name"] = squad_names.get(d.get("squad_id"), "—")
        d["category_name"] = cat_names.get(d.get("category_id"))
        d["process_name"] = proc_names.get(d.get("delivery_process_id"))

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    querystring = request.GET.copy()
    querystring.pop("page", None)
    return render(
        request,
        "documents/list.html",
        {
            "documents": docs,
            "squads": squads,
            "categories": categories,
            "doc_types": doc_types,
            "phases": phases,
            "processes": processes,
            "filters": filters,
            "page": page,
            "total": total,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "base_qs": querystring.urlencode(),
            "nav": "documentos",
        },
    )


def document_upload(request):
    if request.method == "POST":
        doc_type = request.POST.get("doc_type", "").strip()
        if not doc_type:
            messages.error(request, "Tipo de documento é obrigatório.")
            return redirect("upload")
        # doc_type e delivery_process_id são obrigatórios (ADR-0013 / ADR-0007) → sempre no payload.
        # Só os campos verdadeiramente opcionais são filtrados quando vazios.
        data = {
            "delivery_process_id": request.POST.get("delivery_process_id", ""),
            "doc_type": doc_type,
        }
        # opcionais (ADR-0014: delivery_phase/valid_until) — só enviados quando preenchidos
        for field in ("author", "tags", "title", "delivery_phase", "valid_until"):
            value = request.POST.get(field, "").strip()
            if value:
                data[field] = value
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
        phases = client.get("/delivery-phases")
        processes = client.get("/delivery-processes")
    except client.ApiError as exc:
        messages.error(request, str(exc.detail))
        squads, doc_types, phases, processes = [], [], [], []
    procs_by_squad: dict[str, list] = {}
    for p in processes:
        procs_by_squad.setdefault(p["squad_id"], []).append({"id": p["id"], "name": p["name"]})
    return render(
        request,
        "documents/upload.html",
        {
            "squads": squads,
            "doc_types": doc_types,
            "phases": phases,
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
            elif action == "save_delivery":
                # Metadados de ciclo de entrega (ADR-0014) — não alteram classification_source
                payload = {
                    "delivery_phase": request.POST.get("delivery_phase") or None,
                    "valid_until": request.POST.get("valid_until") or None,
                }
                client.patch(f"/documents/{document_id}", json=payload)
                messages.success(request, "Fase/vigência salvas.")
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
            elif action == "delete_document":
                client.delete(f"/documents/{document_id}")
                messages.success(request, "Documento excluído (chunks e vetores removidos).")
                return redirect("document_list")
        except client.ApiError as exc:
            messages.error(request, str(exc.detail))
        return redirect("document_detail", document_id=document_id)

    try:
        doc = client.get(f"/documents/{document_id}")
        links = client.get(f"/documents/{document_id}/links")
        categories = client.get("/categories")
        link_types = client.get("/link-types")
        phases = client.get("/delivery-phases")
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
    ext = (doc.get("original_filename") or "").lower().rsplit(".", 1)[-1]
    doc["previewable"] = ext in PREVIEWABLE_EXTS
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
            "phases": phases,
            "candidates": candidates,
            "nav": "documentos",
        },
    )


def document_file(request, document_id):
    """Proxy do arquivo servido pela API (guardrail: o browser só conhece o Django).

    `?download=1` força attachment; caso contrário, inline para o modal de visualização.
    """
    download = request.GET.get("download") == "1"
    url = settings.API_BASE_URL.rstrip("/") + f"/documents/{document_id}/file"
    try:
        upstream = httpx.get(url, params={"download": "true"} if download else None, timeout=60)
    except httpx.RequestError as exc:
        raise Http404(f"API indisponível ({exc}).")
    if upstream.status_code == 404:
        raise Http404("Arquivo não encontrado.")
    if upstream.status_code >= 400:
        # repassa a falha em vez de servir o corpo de erro como se fosse o arquivo
        raise Http404("Falha ao obter o arquivo do documento.")
    resp = HttpResponse(
        upstream.content,
        content_type=upstream.headers.get("content-type", "application/octet-stream"),
    )
    if "content-disposition" in upstream.headers:
        resp["Content-Disposition"] = upstream.headers["content-disposition"]
    return resp
