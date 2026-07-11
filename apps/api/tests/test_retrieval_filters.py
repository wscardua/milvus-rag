"""WORK-010 / ADR-0015: filtros de retrieval por delivery_phase e tags (campo dinâmico Milvus).

Unitário puro (sem tocar Milvus/Postgres): _map_filters (retriever) e _build_filter_expr
(vectorstore). Integração real fica em test_vectorstore_dynamic_fields.py.
"""
from __future__ import annotations

from app.domain.retrieval.retriever import _map_filters
from app.services.vectorstore import _build_filter_expr, serialize_tags


def test_map_filters_delivery_phase_passthrough():
    out = _map_filters({"delivery_phase": "Testes"})
    assert out == {"delivery_phase": "Testes"}


def test_map_filters_tags_stays_a_list():
    out = _map_filters({"tags": ["billing", "api"]})
    assert out == {"tags": ["billing", "api"]}


def test_map_filters_empty_tags_list_dropped():
    out = _map_filters({"tags": [], "squad": "s1"})
    assert out == {"squad_id": "s1"}


def test_map_filters_combines_scalar_and_tags():
    out = _map_filters({"squad": "s1", "doc_type": "Outro", "tags": ["x"]})
    assert out == {"squad_id": "s1", "doc_type": "Outro", "tags": ["x"]}


def test_map_filters_tags_as_bare_string_becomes_single_item_list():
    """Achado de code review: list("billing") explodia a string em caracteres."""
    out = _map_filters({"tags": "billing"})
    assert out == {"tags": ["billing"]}


def test_serialize_tags():
    assert serialize_tags(["billing", "api"]) == ",billing,api,"
    assert serialize_tags([]) == ""
    assert serialize_tags(None) == ""


def test_build_filter_expr_empty():
    assert _build_filter_expr({}) == ""


def test_build_filter_expr_scalar_equality():
    expr = _build_filter_expr({"doc_type": "Outro"})
    assert expr == 'doc_type == "Outro"'


def test_build_filter_expr_delivery_phase_equality():
    expr = _build_filter_expr({"delivery_phase": "Testes"})
    assert expr == 'delivery_phase == "Testes"'


def test_build_filter_expr_single_tag_like():
    expr = _build_filter_expr({"tags": ["billing"]})
    assert expr == '(tags like "%,billing,%")'


def test_build_filter_expr_multiple_tags_is_or():
    expr = _build_filter_expr({"tags": ["billing", "api"]})
    assert expr == '(tags like "%,billing,%" or tags like "%,api,%")'


def test_build_filter_expr_strips_underscore_wildcard_from_tag():
    """Achado de code review: `_` é coringa de 1 caractere no LIKE do Milvus (confirmado
    contra o Milvus real) — sem remover, "a_b" também casaria com "axb"."""
    expr = _build_filter_expr({"tags": ["a_b"]})
    assert expr == '(tags like "%,ab,%")'


def test_build_filter_expr_combines_scalar_delivery_phase_and_tags_with_and():
    expr = _build_filter_expr({"doc_type": "Outro", "delivery_phase": "Testes", "tags": ["billing"]})
    assert expr == (
        'doc_type == "Outro" and delivery_phase == "Testes" and (tags like "%,billing,%")'
    )


def test_build_filter_expr_escapes_quotes_and_backslash_in_scalar():
    expr = _build_filter_expr({"doc_type": 'x" or 1==1 or "y'})
    assert expr == 'doc_type == "x\\" or 1==1 or \\"y"'


def test_build_filter_expr_strips_delimiter_and_wildcard_from_tag_value():
    # tenta injetar coringa/delimitador no valor da tag pedida no filtro — deve ser sanitizado
    expr = _build_filter_expr({"tags": ['a,b%",c']})
    assert expr == '(tags like "%,ab\\"c,%")'
