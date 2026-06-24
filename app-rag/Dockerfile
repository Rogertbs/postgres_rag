# Usa a imagem oficial do Postgres versão 18.4 como base
FROM postgres:18.4

# Instala dependências do sistema necessárias para compilar extensões
RUN apt-get update && apt-get install -y \
    build-essential \
    cargo \
    git \
    postgresql-server-dev-18 \
    python3 \
    python3-pip \
    postgresql-plpython3-18 \
    && rm -rf /var/lib/apt/lists/*

ENV PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

# Prepara a pasta temporária para baixar o código das extensões
WORKDIR /tmp

# Clona os repositórios oficiais do pgvector e do pgai
RUN git clone https://github.com/pgvector/pgvector.git
RUN git clone --depth 1 --branch pgai-v0.12.1 https://github.com/timescale/pgai.git
# Patch: pgai requer Python <3.13, mas a imagem PG18 vem com Python 3.13
# Adiciona --ignore-requires-python na chamada do pip dentro do build.py
RUN sed -i "s/ install -v/ install --ignore-requires-python -v/g" /tmp/pgai/projects/extension/build.py
# 3. Mudar para a pasta da extensão e rodar o instalador oficial do repositório
WORKDIR /tmp/pgai/projects/extension
RUN python3 build.py build-install
# Opcional: Limpar os arquivos temporários do git para reduzir o tamanho da imagem
WORKDIR /
RUN rm -rf /tmp/pgai

# Compila e instala o pgvector
WORKDIR /tmp/pgvector
RUN make
RUN make install
