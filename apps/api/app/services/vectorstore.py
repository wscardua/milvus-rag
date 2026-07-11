"""Índice vetorial no Milvus (contrato ADR-0002: dim/COSINE/HNSW imutáveis).

Todo vetor referencia um chunk rastreável no Postgres (chunk_id = PK).
Payload filtrável (schema declarado): document_id, squad_id, delivery_process_id, category_id, doc_type (ADR-0007).
Payload filtrável (campo dinâmico, sem alterar o schema — ADR-0015): delivery_phase (igualdade),
tags (string delimitada por vírgula ",tag1,tag2,", filtro OR via LIKE por tag). A coleção é criada
com enable_dynamic_field=True, então esses 2 campos não precisam ser declarados nem exigem
dropar/recriar a coleção — chunks indexados antes desta mudança simplesmente não os têm.
"""
from __future__ import annotations

from pymilvus import DataType, MilvusClient

from app.config import settings

_client: MilvusClient | None = None

_PAYLOAD_FIELDS = ("document_id", "squad_id", "delivery_process_id", "category_id", "doc_type")

# campos dinâmicos (ADR-0015) — fora do schema declarado, não entram em _PAYLOAD_FIELDS
_TAG_DELIMITER = ","


def _escape(value: str) -> str:
    """Escapa valor de usuário antes de embutir numa expressão de filtro Milvus."""
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def serialize_tags(tags: list[str] | None) -> str:
    """['a', 'b'] -> ',a,b,' — sentinelas nas pontas evitam falso-positivo de prefixo no LIKE."""
    if not tags:
        return ""
    return _TAG_DELIMITER + _TAG_DELIMITER.join(tags) + _TAG_DELIMITER


def _escape_tag_for_like(tag: str) -> str:
    """Sanitiza um valor de tag antes de embutir num `LIKE "%...%"`.

    Além do escaping de `"`/`\\`, remove `,` (delimitador — uma tag nunca contém vírgula,
    pois já é o separador usado na entrada) e `%` (coringa do LIKE) do valor, para que um
    filtro malicioso não altere a expressão nem vire um wildcard mais amplo do que o pedido.
    """
    return _escape(tag).replace(_TAG_DELIMITER, "").replace("%", "")


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
    """rows: {chunk_id, vector, document_id, squad_id, delivery_process_id, category_id, doc_type,
    delivery_phase?, tags?}. `delivery_phase`/`tags` (ADR-0015) são campos dinâmicos — opcionais,
    aceitos pelo Milvus sem estarem no schema declarado (enable_dynamic_field=True). `tags`, se
    presente, já deve vir serializada (`serialize_tags`) pelo chamador (domain/ingestion/pipeline.py).
    """
    if rows:
        _c().upsert(collection_name=settings.milvus_collection, data=rows)


def sync_document_fields(document_id: str, fields: dict) -> int:
    """Atualiza campos de payload (declarados ou dinâmicos) dos chunks JÁ indexados de um
    documento, sem reembeder/reextrair (edição de metadado via `PATCH`, não de conteúdo).

    `fields`: `{nome: valor}`. `valor=None` **remove** o campo do payload (só faz sentido
    para campo dinâmico — ex.: `delivery_phase` limpo); campo declarado (`_PAYLOAD_FIELDS`)
    nunca pode ficar ausente da linha, então o chamador deve passar `""` em vez de `None`
    para "sem valor" nesses casos.

    Milvus não tem "update parcial de campo": um `upsert` pela mesma `chunk_id` primary key
    substitui a linha inteira — por isso a linha é lida por completo (`query(output_fields=["*"])`,
    inclui `vector`) antes de reescrever só as chaves pedidas.

    Retorna o número de chunks atualizados (0 se o documento ainda não tem chunks indexados —
    não é erro, só não há nada pra sincronizar ainda).
    """
    rows = _c().query(
        collection_name=settings.milvus_collection,
        filter=f'document_id == "{_escape(document_id)}"',
        output_fields=["*"],
    )
    if not rows:
        return 0
    for row in rows:
        row["vector"] = [float(x) for x in row["vector"]]  # numpy float32 → float nativo
        for key, value in fields.items():
            if value is None:
                row.pop(key, None)
            else:
                row[key] = value
    _c().upsert(collection_name=settings.milvus_collection, data=rows)
    return len(rows)


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


def _build_filter_expr(filters: dict) -> str:
    """Monta a expressão de filtro Milvus a partir de `filters` (testável sem tocar o Milvus).

    Campos declarados em `_PAYLOAD_FIELDS` usam igualdade. Via campo dinâmico (ADR-0015):
    `delivery_phase` usa igualdade; `tags` (lista de strings) vira um `OR` de `LIKE` — hit
    incluído se tiver qualquer uma das tags pedidas.
    """
    exprs = []
    for field in _PAYLOAD_FIELDS:
        val = filters.get(field)
        if val:
            # escapa aspas/barra para evitar injeção na expressão de filtro do Milvus
            exprs.append(f'{field} == "{_escape(val)}"')

    delivery_phase = filters.get("delivery_phase")
    if delivery_phase:
        exprs.append(f'delivery_phase == "{_escape(delivery_phase)}"')

    tags = filters.get("tags")
    if tags:
        # OR: hit incluído se tiver qualquer uma das tags pedidas (ADR-0015)
        tag_exprs = [f'tags like "%{_TAG_DELIMITER}{_escape_tag_for_like(t)}{_TAG_DELIMITER}%"' for t in tags]
        exprs.append("(" + " or ".join(tag_exprs) + ")")

    return " and ".join(exprs)


def search(vector: list[float], top_k: int, filters: dict | None = None) -> list[dict]:
    """Retorna [{chunk_id, document_id, score}] ordenado por similaridade (COSINE)."""
    expr = _build_filter_expr(filters or {})
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
