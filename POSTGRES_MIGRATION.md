# BusZapp — Migração para PostgreSQL

## O que foi alterado

| Arquivo | Mudança |
|---|---|
| `requirements.txt` | Adicionado `psycopg2-binary` e `Flask-Migrate` |
| `src/config.py` | `DATABASE_URL` agora usa PostgreSQL; pool de conexões configurado; correção automática do prefixo `postgres://` → `postgresql://` |
| `src/main.py` | Flask-Migrate integrado (`flask db migrate / upgrade`) |
| `.env` | `DATABASE_URL` aponta para PostgreSQL |
| `.env.example` | Novo arquivo de referência com exemplos de URL |
| `migrate_sqlite_to_postgres.py` | Script para copiar dados do SQLite → PostgreSQL |

---

## Passo a passo

### 1. Instale as dependências

```bash
pip install -r requirements.txt
```

### 2. Configure o .env

Edite `.env` e ajuste `DATABASE_URL`:

```
# Local
DATABASE_URL=postgresql://postgres:sua_senha@localhost:5432/buszapp

# Render (cole a Internal Database URL)
DATABASE_URL=postgresql://buszapp_user:xxxx@dpg-xxx.render.com/buszapp

# Supabase
DATABASE_URL=postgresql://postgres:[senha]@db.[ref].supabase.co:5432/postgres
```

### 3. Crie o banco no PostgreSQL (se local)

```sql
CREATE DATABASE buszapp;
```

### 4. Inicialize o Flask-Migrate

```bash
flask db init        # apenas na primeira vez — cria a pasta migrations/
flask db migrate -m "initial schema"
flask db upgrade     # cria as tabelas no PostgreSQL
```

> **Alternativa sem Migrate:** o app ainda chama `db.create_all()` ao iniciar,
> então subir o servidor já cria as tabelas automaticamente.

### 5. (Opcional) Migre dados do SQLite

Se você já tinha dados no banco SQLite (`src/instance/app.db`):

```bash
python migrate_sqlite_to_postgres.py
```

O script é seguro para rodar mais de uma vez — ele pula tabelas que já têm dados.

### 6. Suba o servidor

```bash
python -m src.main
# ou
flask run --host=0.0.0.0 --port=8080
```

---

## Variáveis de ambiente completas

| Variável | Descrição |
|---|---|
| `DATABASE_URL` | URL de conexão PostgreSQL |
| `SECRET_KEY` | Chave secreta Flask (mude em produção!) |
| `GOOGLE_API_KEY` | Chave da API Google Maps |
| `ROUTE_ORIGIN_LAT/LON` | Coordenadas de origem da rota |
| `ROUTE_DEST_LAT/LON` | Coordenadas de destino da rota |
| `FLASK_ENV` | `development` ou `production` |

---

## Provedores recomendados (gratuitos)

| Provedor | Plano grátis | Observação |
|---|---|---|
| **Supabase** | 500 MB | Interface visual ótima |
| **Render** | 1 GB (90 dias) | Integra bem com o deploy do Flask |
| **Railway** | 1 GB | Deploy simples via GitHub |
| **Neon** | 512 MB | Serverless, excelente para dev |
