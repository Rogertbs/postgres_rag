# RAG PG — Chatbot Privado com PostgreSQL + pgvector + pgai

Serviço de banco de dados vetorial para chatbot privado, utilizando PostgreSQL 18 com as extensões **pgvector** (armazenamento e busca de embeddings) e **pgai** (integração com Ollama para geração de embeddings e LLM).

---

## Arquitetura — Fluxo RAG (rag_teste.py)

```
┌──────────────────────────────────────────────────────────────┐
│  Usuário digita a pergunta                                   │
│  Ex: "Onde nasce o rio Gange?"                               │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  1. Embedding da pergunta                                    │
│     Ollama (nomic-embed-text) → vetor 768 dimensões          │
│     Servidor remoto: $OLLAMA_HOST                            │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  2. RETRIEVAL — Busca por similaridade                       │
│     PostgreSQL + pgvector (Docker :5434)                     │
│     SELECT ... ORDER BY embedding <=> pergunta LIMIT 3       │
│     Distância cosseno (<=>) — quanto menor, mais similar     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  3. PREVIEW — Documentos recuperados                         │
│     Mostra similaridade de cada documento                    │
│     Usuário vê se os resultados fazem sentido                │
│     Confirma com [Enter] ou pula com [n]                     │
└────────────────────────┬─────────────────────────────────────┘
                         │ (usuário confirma)
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  4. AUGMENTED + GENERATION                                   │
│     Monta prompt: CONTEXTO + PERGUNTA                        │
│     Ollama (qwen2.5:1.5b) gera a resposta                    │
│     Ex: "O Gange nasce nas geleiras de Uttarakhand..."       │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  Resposta exibida no terminal                                │
└──────────────────────────────────────────────────────────────┘
```

### Componentes

| Camada         | Tecnologia                        | Onde roda        |
|----------------|-----------------------------------|------------------|
| Embedding      | Ollama + nomic-embed-text (768d)  | Servidor remoto  |
| Busca vetorial | PostgreSQL 18 + pgvector          | Docker (:5434)   |
| LLM / Geração  | Ollama + qwen2.5:1.5b             | Servidor remoto  |
| Orquestração   | Python (ollama, pgvector, psycopg2) | Script local   |

---

## Estrutura do Projeto

```
rag_pg/
├── rag_teste.py            # Script principal — RAG interativo via terminal
├── seed_data.sql           # Popula o banco com dados de teste (Himalaia indiano)
├── Dockerfile              # Imagem PostgreSQL 18 + pgvector + pgai
├── docker-compose.yaml     # Orquestração do container
├── activate-extension.sql  # Ativa extensões no startup do banco
├── create_tables.sql       # Criação da tabela items
├── embed_test.sql          # Testes de embedding e similaridade via SQL
├── pg_hba.conf             # Configuração de autenticação
└── postgres_data/          # Volume de dados persistente
```

---

## Stack

| Componente    | Tecnologia                     |
|---------------|--------------------------------|
| Banco         | PostgreSQL 18 + pgvector       |
| Embedding     | Ollama (nomic-embed-text, 768d)|
| LLM           | Ollama (qwen2.5:1.5b)         |
| Container     | Docker + Docker Compose        |
| Script        | Python 3 + ollama + pgvector + psycopg2 |

---

## Pré-requisitos

- Docker e Docker Compose instalados
- [Ollama](https://ollama.com) rodando em servidor remoto com os modelos:
  - `nomic-embed-text` (embedding)
  - `qwen2.5:1.5b` (LLM)
- Python 3 com as bibliotecas:
  ```bash
  pip3 install pgvector psycopg2-binary ollama
  ```

---

## Como subir

```bash
cd /ez/services/rag_pg
docker compose up -d --build
```

O banco estará disponível em `localhost:5434`:
- **Database:** `vectordb`
- **Usuário:** `postgres`
- **Senha:** `postgres`

---

## Como testar

### Via script Python (recomendado)

```bash
# Aponte para o servidor Ollama remoto
export OLLAMA_HOST=http://<IP_DO_SERVIDOR>:11434

# Execute o RAG interativo
python3 rag_teste.py
```

O fluxo interativo:
1. Digite uma pergunta sobre o Himalaia
2. Veja os documentos recuperados com similaridade
3. Confirme [Enter] para gerar a resposta via LLM, ou [n] para pular

### Variáveis de ambiente

| Variável     | Default                  | Descrição                    |
|-------------|--------------------------|------------------------------|
| OLLAMA_HOST | http://172.16.200.20:11434 | Servidor Ollama remoto     |
| DB_HOST     | localhost                | Host do PostgreSQL           |
| DB_PORT     | 5434                     | Porta do PostgreSQL          |
| DB_NAME     | vectordb                 | Nome do banco                |
| DB_USER     | postgres                 | Usuário do banco             |
| DB_PASS     | postgres                 | Senha do banco               |

### Via SQL (testes diretos no banco)

```bash
# Popular com dados de teste
docker exec -i postgres-ai-postgres-1 psql -U postgres -d vectordb < seed_data.sql

# Testes de embedding e similaridade
docker exec -i postgres-ai-postgres-1 psql -U postgres -d vectordb < embed_test.sql
```

---

## Comandos úteis

```bash
# Ver logs
docker compose logs -f

# Derrubar e limpar volumes
docker compose down -v

# Recriar do zero
docker compose up -d --build --force-recreate
```
