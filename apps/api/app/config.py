"""Configuração única do backend (ADR-0006): tudo vem de env, nada hardcoded.

Migrar para serviços gerenciados (Postgres gerenciado, Zilliz Cloud, LLM na nuvem)
é troca de .env — sem mudança de código.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Banco
    database_url: str = "postgresql+psycopg2://rag:rag@localhost:5432/rag"

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "rag_chunks"

    # LM Studio (embeddings + chat, API OpenAI-compatível)
    lm_studio_base_url: str = "http://localhost:1234/v1"
    lm_studio_api_key: str = "lm-studio"
    embedding_model: str = "embeddinggemma-300m"
    embedding_dim: int = 768
    chat_model: str = "local-chat-model"

    # Upload
    upload_dir: str = "../../data/uploads"
    max_upload_mb: int = 50

    # Worker de ingestão (ADR-0004 / ADR-0009) — segundos, exceto max_attempts
    worker_poll_interval: int = 5
    worker_heartbeat_interval: int = 30
    worker_visibility_timeout: int = 300  # 5 min
    worker_max_attempts: int = 3
    worker_retry_backoff_base: int = 60  # backoff: base * 2^(attempts-1)

    # Retrieval
    retrieval_top_k: int = 5
    retrieval_min_score: float = 0.3  # abaixo disto: "sem contexto suficiente" (COSINE)
    # Vigência (ADR-0014): hits de documentos vencidos (valid_until < hoje) têm o score
    # multiplicado por este fator e são reordenados — rebaixados, não excluídos. 1.0 = desliga.
    retrieval_expired_score_factor: float = 0.5

    # Chunking (ADR-0002: chunk < 2048 tokens do modelo)
    chunk_size_words: int = 350
    chunk_overlap_words: int = 60

    # Chunking por doc_type (ADR-0013; ADR-0006: tudo por env; fallback = chunk_size_words/chunk_overlap_words)
    chunk_size_procedimento_runbook: int = 150
    chunk_overlap_procedimento_runbook: int = 20
    chunk_size_transcricao_reuniao: int = 200
    chunk_overlap_transcricao_reuniao: int = 50
    chunk_size_ata_reuniao: int = 200
    chunk_overlap_ata_reuniao: int = 40
    chunk_size_codigo_fonte: int = 120
    chunk_overlap_codigo_fonte: int = 15
    chunk_size_planilha: int = 80
    chunk_overlap_planilha: int = 10
    chunk_size_contrato_legal: int = 500
    chunk_overlap_contrato_legal: int = 100
    chunk_size_manual_guia: int = 400
    chunk_overlap_manual_guia: int = 80
    chunk_size_relatorio: int = 400
    chunk_overlap_relatorio: int = 70
    chunk_size_documento_tecnico: int = 350
    chunk_overlap_documento_tecnico: int = 60
    chunk_size_proposta_tecnica: int = 300
    chunk_overlap_proposta_tecnica: int = 60
    chunk_size_especificacao_requisito: int = 300
    chunk_overlap_especificacao_requisito: int = 60
    chunk_size_base_conhecimento: int = 350
    chunk_overlap_base_conhecimento: int = 60
    chunk_size_apresentacao: int = 300
    chunk_overlap_apresentacao: int = 50
    # doc_type "Outro" e qualquer valor não mapeado usam chunk_size_words/chunk_overlap_words

    # Vision — descrição de imagens durante ingestão (ADR-0012)
    vision_enabled: bool = True
    # Modelo vision: usa o mesmo servidor LM Studio (lm_studio_base_url).
    # Default = mesmo modelo de chat (gemma-3-4b-it-qat tem capability Vision).
    # Para trocar: basta mudar VISION_MODEL no .env — zero mudança de código.
    vision_model: str = "gemma-3-4b-it-qat"
    vision_max_tokens: int = 800  # tabelas densas não truncam (entra no chunking com o texto)
    # Render da região da imagem na página em alta DPI (em vez do bitmap embutido):
    # normaliza colorspace, captura a imagem como exibida e garante tamanho legível.
    vision_render_dpi: int = 200


settings = Settings()
