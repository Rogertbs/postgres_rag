-- ver se extensoes foram instaladas
SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('vector', 'ai');




select set_config('ai.ollama_host', 'http://172.16.200.20:11434', false);

-- Teste gerando embedding
select
    ai.ollama_embed(
        'nomic-embed-text',
        'um texto falando sobre como a inteligência artificial é incrível'
    ) as embed;

-- Gerar embedding e inserir na tabela
INSERT INTO items (embedding, description) VALUES
( ai.ollama_embed('nomic-embed-text', 'um texto falando sobre como a inteligência artificial é incrível'), 'um texto falando sobre como a inteligência artificial é incrível'),
( ai.ollama_embed('nomic-embed-text', 'um texto falando sobre como fazer exercícios físicos é incrível'), 'um texto falando sobre como fazer exercícios físicos é incrível');


-- Outro exemplo embedding
INSERT INTO items (embedding, description) VALUES
( ai.ollama_embed('nomic-embed-text', 'o Himalaia é a maior cordilheira do mundo, localizada no norte da Índia, abrigando o Monte Everest e sendo considerada sagrada por diversas culturas'), 'o Himalaia é a maior cordilheira do mundo, localizada no norte da Índia, abrigando o Monte Everest e sendo considerada sagrada por diversas culturas'),
( ai.ollama_embed('nomic-embed-text', 'a Royal Enfield Himalayan é uma motocicleta adventure de 450cc, projetada para encarar estradas difíceis e trilhas off-road, inspirada nas paisagens do Himalaia'), 'a Royal Enfield Himalayan é uma motocicleta adventure de 450cc, projetada para encarar estradas difíceis e trilhas off-road, inspirada nas paisagens do Himalaia');


select * from items

-- buscando texto por similaridade de cosceno <=>
-- https://github.com/pgvector/pgvector?tab=readme-ov-file#querying
SELECT *,
    embedding <=> ai.ollama_embed('nomic-embed-text', 'IA') as distance
FROM items
ORDER BY embedding <=> ai.ollama_embed('nomic-embed-text', 'IA');


SELECT description,
    embedding <=> ai.ollama_embed('nomic-embed-text', 'IA') as distance
FROM items
ORDER BY embedding <=> ai.ollama_embed('nomic-embed-text', 'IA');

SELECT description,
    embedding <=> ai.ollama_embed('nomic-embed-text', 'inteligência artificial') as distance
FROM items
ORDER BY distance asc;

SELECT description,
    embedding <=> ai.ollama_embed('nomic-embed-text', 'Onde fica o Himalaia') as distance
FROM items
ORDER BY embedding <=> ai.ollama_embed('nomic-embed-text', 'Onde fica o Himalaia');