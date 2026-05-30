-- ver se extensoes foram instaladas
SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('vector', 'ai');




select set_config('ai.ollama_host', 'http://host.docker.internal:11434', false);

CREATE TABLE items (
    id bigserial PRIMARY KEY,
    embedding vector(768),
    description text
);

select
    ollama_embed(
        'nomic-embed-text',
        'um texto falando sobre como a inteligência artificial é incrível'
    ) as embed;

INSERT INTO items (embedding, description) VALUES
( ollama_embed('nomic-embed-text', 'um texto falando sobre como a inteligência artificial é incrível'), 'um texto falando sobre como a inteligência artificial é incrível'),
( ollama_embed('nomic-embed-text', 'um texto falando sobre como fazer exercícios físicos é incrível'), 'um texto falando sobre como fazer exercícios físicos é incrível');

select * from items


-- https://github.com/pgvector/pgvector?tab=readme-ov-file#querying
SELECT *,
    embedding <=> ollama_embed('nomic-embed-text', 'IA') as distance
FROM items
ORDER BY embedding <=> ollama_embed('nomic-embed-text', 'IA');


