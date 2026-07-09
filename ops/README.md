# ops — Infra local (Podman)

Sobe **PostgreSQL** (metadados do RAG) e **Milvus standalone** (índice vetorial, que requer **etcd** + **minio**).

## Pré-requisitos

- Podman com máquina iniciada: `podman machine init` (1ª vez) e `podman machine start`.
- `podman compose` disponível (usa docker-compose v2 ou podman-compose por baixo).

## Subir / parar

```bash
cd ops
cp .env.example .env         # 1ª vez; ajuste credenciais/portas se quiser

podman compose up -d         # sobe os 4 serviços
podman compose ps            # status + health
podman compose logs -f milvus
podman compose down          # PARA os serviços — PRESERVA os dados
```

## Persistência (dados NÃO efêmeros, dentro do projeto)

Os dados ficam em **bind mounts dentro do projeto**, em `data/volumes/` (configurável por `DATA_DIR`), e sobrevivem a restart, reboot e `down`:

```
data/
├── uploads/            # arquivos enviados (app)
└── volumes/            # dados dos containers (infra)
    ├── postgres/  ├── milvus/  ├── etcd/  └── minio/
```

```bash
du -sh ../data/volumes/*       # inspecionar tamanho por serviço
```

> ⚠️ **Perda de dados:** apagar a pasta `data/volumes/` (ou `podman compose down -v`).
> O `down` normal **não** apaga nada. `data/` é gitignored.

### Backup rápido

Como os dados estão no host, basta arquivar a pasta:

```bash
tar czf backup-data.tgz -C .. data/volumes
```

## Portas

| Serviço | Porta | Uso |
|---|---|---|
| Postgres | 5432 | conexão do backend |
| Milvus | 19530 | gRPC (pymilvus) |
| Milvus | 9091 | métricas / `healthz` |
| MinIO | 9000 / 9001 | API / console web |

## Conexão a partir do backend (`apps/api`)

- Postgres: `postgresql://rag:rag@localhost:5432/rag`
- Milvus: `localhost:19530`

## Inspeção opcional (Attu — GUI do Milvus)

Para inspecionar coleções, rode o Attu apontando para o Milvus:

```bash
podman run -d --name attu -p 8000:3000 \
  -e MILVUS_URL=host.containers.internal:19530 zilliz/attu:latest
# abra http://localhost:8000
```
