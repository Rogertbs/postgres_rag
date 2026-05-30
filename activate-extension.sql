-- 1. Cria a extensão pgvector para permitir o armazenamento de vetores (embeddings)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Cria a extensão para funções de IA (caso você esteja usando o pgai)
-- Se você ainda não estiver usando o pgai, pode remover a linha abaixo.
-- CREATE EXTENSION IF NOT EXISTS ai CASCADE;

-- 3. Mensagem de confirmação no log do banco ao iniciar
DO $$ 
BEGIN
    RAISE NOTICE 'Extensões de IA e Vetores ativadas com sucesso!';
END $$;
