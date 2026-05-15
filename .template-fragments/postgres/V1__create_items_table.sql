CREATE TABLE items
(
    id          BIGINT          GENERATED ALWAYS AS IDENTITY,
    name        VARCHAR(20)     NOT NULL,
    description VARCHAR(100)    NOT NULL,
    PRIMARY KEY (id)
);

