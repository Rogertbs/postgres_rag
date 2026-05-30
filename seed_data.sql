-- ============================================================
-- Seed Data — Popula o banco com dados de teste
-- Tema: Himalaia Indiano
-- Cada INSERT gera o embedding automaticamente via pgai + Ollama
-- ============================================================

-- Configurar host do Ollama (servidor remoto)
select set_config('ai.ollama_host', 'http://172.16.200.20:11434', false);

-- Inserir 10 registros sobre o Himalaia indiano
INSERT INTO items (embedding, description) VALUES

( ai.ollama_embed('nomic-embed-text', 'a região de Ladakh, situada no Himalaia indiano, é conhecida por suas paisagens desérticas de alta altitude, passos de montanha extremos e forte influência da cultura budista tibetana'), 'a região de Ladakh, situada no Himalaia indiano, é conhecida por suas paisagens desérticas de alta altitude, passos de montanha extremos e forte influência da cultura budista tibetana'),

( ai.ollama_embed('nomic-embed-text', 'o rio Gange nasce nas geleiras eternas do Himalaia, na região de Uttarakhand, descendo pelas montanhas até se tornar o rio mais sagrado e vital para a população da Índia'), 'o rio Gange nasce nas geleiras eternas do Himalaia, na região de Uttarakhand, descendo pelas montanhas até se tornar o rio mais sagrado e vital para a população da Índia'),

( ai.ollama_embed('nomic-embed-text', 'o leopardo-das-neves é um felino raro e místico que habita as encostas rochosas e frias do Himalaia, possuindo uma pelagem espessa que o camufla perfeitamente na neve'), 'o leopardo-das-neves é um felino raro e místico que habita as encostas rochosas e frias do Himalaia, possuindo uma pelagem espessa que o camufla perfeitamente na neve'),

( ai.ollama_embed('nomic-embed-text', 'a cidade de Rishikesh está localizada sopé do Himalaia, no norte da Índia, sendo mundialmente famosa como a capital do yoga e um importante centro de meditação espiritual'), 'a cidade de Rishikesh está localizada sopé do Himalaia, no norte da Índia, sendo mundialmente famosa como a capital do yoga e um importante centro de meditação espiritual'),

( ai.ollama_embed('nomic-embed-text', 'o Khardung La é uma das estradas motorizáveis mais altas do mundo, cruzando a cordilheira do Himalaia e servindo como um desafio extremo para motociclistas e jipes'), 'o Khardung La é uma das estradas motorizáveis mais altas do mundo, cruzando a cordilheira do Himalaia e servindo como um desafio extremo para motociclistas e jipes'),

( ai.ollama_embed('nomic-embed-text', 'o Vale das Flores é um parque nacional indiano situado no alto Himalaia Ocidental, famoso por seus prados cobertos de flora alpina endêmica e paisagens alpinas intocadas'), 'o Vale das Flores é um parque nacional indiano situado no alto Himalaia Ocidental, famoso por seus prados cobertos de flora alpina endêmica e paisagens alpinas intocadas'),

( ai.ollama_embed('nomic-embed-text', 'a colheita do chá de Darjeeling ocorre nas encostas úmidas e enevoadas localizadas nas ramificações do Himalaia, produzindo uma das bebidas mais finas e valorizadas do mundo'), 'a colheita do chá de Darjeeling ocorre nas encostas úmidas e enevoadas localizadas nas ramificações do Himalaia, produzindo uma das bebidas mais finas e valorizadas do mundo'),

( ai.ollama_embed('nomic-embed-text', 'o Monte Kanchenjunga é a terceira montanha mais alta do mundo e o pico mais elevado da Índia, erguendo-se majestosamente na fronteira com o Nepal na cordilheira do Himalaia'), 'o Monte Kanchenjunga é a terceira montanha mais alta do mundo e o pico mais elevado da Índia, erguendo-se majestosamente na fronteira com o Nepal na cordilheira do Himalaia'),

( ai.ollama_embed('nomic-embed-text', 'o vilarejo de Manali, cercado por florestas de pinheiros e picos nevados do Himalaia, serve como base principal para expedições de trekking, esqui e esportes de aventura na Índia'), 'o vilarejo de Manali, cercado por florestas de pinheiros e picos nevados do Himalaia, serve como base principal para expedições de trekking, esqui e esportes de aventura na Índia'),

( ai.ollama_embed('nomic-embed-text', 'os antigos monastérios budistas, como o de Thiksey, desafiam a gravidade ao serem construídos encrustados nas rochas verticais das montanhas do Himalaia indiano'), 'os antigos monastérios budistas, como o de Thiksey, desafiam a gravidade ao serem construídos encrustados nas rochas verticais das montanhas do Himalaia indiano');

-- Verificar inserção
SELECT id, description FROM items ORDER BY id;
