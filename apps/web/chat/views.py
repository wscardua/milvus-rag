"""Tela de Chat multi-turno (WORK-012, ADR-0016/0017) — cliente HTTP puro de /conversations e /query.

Sem lógica de retrieval/prompt aqui: a condensação e a montagem do contexto acontecem
inteiramente na API. Esta view só orquestra as chamadas HTTP (contrato `conversations` /
`query-and-citations`) e apresenta o resultado.
"""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect, render

from core import client


def chat(request, conversation_id=None):
    conversation_id = str(conversation_id) if conversation_id else None
    try:
        conversations = client.get("/conversations")
    except client.ApiError as exc:
        conversations = []
        messages.error(request, str(exc.detail))

    conversation = None
    if conversation_id:
        try:
            conversation = client.get(f"/conversations/{conversation_id}")
        except client.ApiError as exc:
            if exc.status == 404:
                messages.error(request, "Conversa não encontrada.")
                return redirect("chat")
            messages.error(request, str(exc.detail))
            return redirect("chat")

    if request.method == "POST":
        question = request.POST.get("question", "").strip()
        if not question:
            messages.error(request, "Pergunta vazia.")
            return redirect("chat_thread", conversation_id=conversation_id) if conversation_id else redirect("chat")

        target_id = conversation_id
        if target_id is None:
            try:
                target_id = client.post("/conversations", json={})["id"]
            except client.ApiError as exc:
                messages.error(request, str(exc.detail))
                return redirect("chat")

        try:
            # timeout maior que o default: turnos de acompanhamento somam a chamada de
            # query condensation (ADR-0017) antes da geração da resposta.
            client.post(
                "/query",
                json={"question": question, "conversation_id": target_id, "top_k": 5},
                timeout=120,
            )
        except client.ApiError as exc:
            messages.error(request, str(exc.detail))
        return redirect("chat_thread", conversation_id=target_id)

    return render(
        request,
        "chat/chat.html",
        {
            "conversations": conversations,
            "conversation": conversation,
            "nav": "chat",
        },
    )
