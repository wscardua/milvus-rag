"""Índice vetorial no Milvus (contrato ADR-0002: dim/COSINE/HNSW imutáveis).

Todo vetor referencia um chunk rastreável no Postgres (chunk_id = PK).
Payload filtrável: document_id, squad_id, delivery_process_id, category_id, doc_type (ADR-0007).
"""
from __future__ import annotations

from pymilvus import DataType, MilvusClient

from app.config import settings

_client: MilvusClient | None = None

_PAYLOAD_FIELDS = ("document_id", "squad_id", "delivery_process_id", "category_id", "doc_type")


def _c() -> MilvusClient:
    global _client
    if _client is None:
        _client = MilvusClient(uri=f"http://{settings.milvus_host}:{settings.milvus_port}")
        _ensure_collection(_client)
    return _client


def _ensure_collection(client: MilvusClient) -> None:
    name = settings.milvus_collection
    if client.has_collection(name):
        client.load_collection(name)
        return
    schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
    schema.add_field("chunk_id", DataType.VARCHAR, is_primary=True, max_length=64)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=settings.embedding_dim)
    for f in _PAYLOAD_FIELDS:
        schema.add_field(f, DataType.VARCHAR, max_length=120)
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="HNSW",
        metric_type="COSINE",
        params={"M": 16, "efConstruction": 200},
    )
    client.create_collection(name, schema=schema, index_params=index_params)
    client.load_collection(name)


def upsert_chunks(rows: list[dict]) -> None:
    """rows: {chunk_id, vector, document_id, squad_id, delivery_process_id, category_id, doc_type}."""
    if rows:
        _c().upsert(collection_name=settings.milvus_collection, data=rows)


def delete_by_document(document_id: str) -> None:
    _c().delete(collection_name=settings.milvus_collection, filter=f'document_id == "{document_id}"')


def ping() -> bool:
    """Conecta e diz se a coleção existe — SEM criá-la (para /health).

    Não usa `_c()` de propósito: o health check é somente-leitura e não deve
    provocar `_ensure_collection` (efeito colateral de criar a coleção).
    """
    client = _client if _client is not None else MilvusClient(
        uri=f"http://{settings.milvus_host}:{settings.milvus_port}"
    )
    return bool(client.has_collection(settings.milvus_collection))


def search(vector: list[float], top_k: int, filters: dict | None = None) -> list[dict]:
    """Retorna [{chunk_id, document_id, score}] ordenado por similaridade (COSINE)."""
    exprs = []
    for field in _PAYLOAD_FIELDS:
        val = (filters or {}).get(field)
        if val:
            # escapa aspas/barra para evitar injeção na expressão de filtro do Milvus
            safe = str(val).replace("\\", "\\\\").replace('"', '\\"')
            exprs.append(f'{field} == "{safe}"')
    expr = " and ".join(exprs) if exprs else ""
    res = _c().search(
        collection_name=settings.milvus_collection,
        data=[vector],
        limit=top_k,
        filter=expr,
        output_fields=["document_id"],
        search_params={"metric_type": "COSINE"},
    )
    hits = res[0] if res else []
    return [
        {
            "chunk_id": h["chunk_id"],
            "document_id": h.get("entity", {}).get("document_id"),
            "score": h["distance"],
        }
        for h in hits
    ]
