# ONGP no GitHub

Este repositorio esta preparado para uso em GitHub Actions, GitHub Container Registry e GitHub Codespaces.

## Secrets obrigatorios

Configure os mesmos nomes em dois lugares, conforme o uso:

- `Settings -> Secrets and variables -> Actions -> New repository secret`
- `Settings -> Secrets and variables -> Codespaces -> New repository secret`

- `CGU_API_KEY`
- `PORTAL_TRANSPARENCIA_API_KEY`
- `OPENAI_API_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

## GitHub Actions

O workflow `.github/workflows/smoke.yml` executa:

- compilacao do backend FastAPI;
- build do frontend Next.js;
- validacao do `docker-compose.yml`;
- build e publicacao das imagens no GHCR:
  - `ghcr.io/<owner>/<repo>-api:latest`
  - `ghcr.io/<owner>/<repo>-web:latest`

Use `Actions -> ONGP GitHub Runtime -> Run workflow` para rodar manualmente.

## Codespaces

Abra `Code -> Codespaces -> Create codespace on main`.

O devcontainer instala Python, Node e Docker-in-Docker, encaminha as portas e inicia a stack com `docker compose up -d --build`:

- Web: porta `3000`
- API: porta `8000`
- Neo4j: porta `7474`
- Elasticsearch: porta `9200`
- Prometheus: porta `9090`
- Grafana: porta `3001`

Para reiniciar tudo dentro do Codespace:

```bash
docker compose up -d --build
```

Para OAuth real do Google em Codespaces, cadastre no Google Cloud Console a URL de callback gerada pelo Codespace:

```text
https://<nome-do-codespace>-8000.app.github.dev/api/v1/auth/oauth/google/callback
```
