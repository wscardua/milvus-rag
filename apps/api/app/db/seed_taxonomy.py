"""Seed idempotente da taxonomia (ADR-0007).

Fonte da verdade: docs/specs/reference/taxonomy.md. Rode com:
    python -m app.db.seed_taxonomy
"""
from __future__ import annotations

from sqlalchemy import select

from app.db.base import SessionLocal
from app.db.models import DOC_TYPES, Category, Subcategory  # noqa: F401 (DOC_TYPES documentado abaixo)

# category -> subcategorias (espelha reference/taxonomy.md)
TAXONOMY: dict[str, list[str]] = {
    "Produto & Discovery": [
        "Visão de Produto", "Requisitos / User Stories", "Pesquisa / Discovery", "Roadmap",
    ],
    "Arquitetura & Engenharia": [
        "Arquitetura de Solução", "ADR / Decisão Técnica", "APIs & Integrações", "Modelo de Dados",
    ],
    "Qualidade & Testes": [
        "Estratégia de Testes", "Casos de Teste", "Critérios de Aceite", "Relatório de Bugs",
    ],
    "Operações & Infra": [
        "CI/CD", "Observabilidade", "Runbook / Operação", "Infraestrutura",
    ],
    "Segurança & Compliance": [
        "Segurança da Informação", "LGPD / Privacidade", "Auditoria", "Gestão de Acessos",
    ],
    "Gestão & Processos Ágeis": [
        "Planning", "Daily", "Review / Demo", "Retrospectiva", "Refinement", "Métricas & Indicadores",
    ],
    "Governança & Negócio": [
        "Contratos", "SLA / Acordos", "Financeiro", "Políticas Internas",
    ],
}

# doc_type é enum lógico validado na aplicação (não vira tabela) — definido em app.db.models.DOC_TYPES


def seed() -> None:
    session = SessionLocal()
    created_cat = created_sub = 0
    try:
        for cat_name, subs in TAXONOMY.items():
            category = session.scalar(select(Category).where(Category.name == cat_name))
            if category is None:
                category = Category(name=cat_name)
                session.add(category)
                session.flush()
                created_cat += 1
            for sub_name in subs:
                exists = session.scalar(
                    select(Subcategory).where(
                        Subcategory.category_id == category.id,
                        Subcategory.name == sub_name,
                    )
                )
                if exists is None:
                    session.add(Subcategory(category_id=category.id, name=sub_name))
                    created_sub += 1
        session.commit()
        print(f"Seed OK: +{created_cat} categorias, +{created_sub} subcategorias (idempotente).")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
