CREATE TABLE items (
    id bigserial PRIMARY KEY,
    embedding vector(768),
    description text
);
