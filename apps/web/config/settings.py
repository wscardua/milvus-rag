"""Settings do Django (apps/web) — cliente da API, sem dados de domínio.

Sessão e mensagens usam cookies assinados (sem banco): a UI não persiste domínio,
que vive no FastAPI/Postgres (guardrail Django=cliente). Config por env (ADR-0006).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = ["*"]

# Base da API FastAPI (apps/api) — a UI só fala com ela via HTTP.
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.messages",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Sessão/mensagens sem banco (cookies assinados) — nenhum DB de domínio na UI.
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"

WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {}  # a UI não usa ORM/banco próprio

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
