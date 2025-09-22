# Arquivo: create_tables.py
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

sql_commands = """
CREATE TABLE IF NOT EXISTS pilotos (
  id SERIAL PRIMARY KEY,
  nome VARCHAR(255) NOT NULL,
  equipe VARCHAR(255) NOT NULL,
  foto VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS corridas (
  id SERIAL PRIMARY KEY,
  nome VARCHAR(255) NOT NULL,
  data_corrida DATE NOT NULL,
  votacao_fechada BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS votos (
  id SERIAL PRIMARY KEY,
  id_corrida INTEGER NOT NULL REFERENCES corridas(id) ON DELETE CASCADE,
  id_piloto INTEGER NOT NULL REFERENCES pilotos(id) ON DELETE CASCADE,
  ip_usuario VARCHAR(255) NOT NULL,
  UNIQUE (id_corrida, ip_usuario)
);

CREATE TABLE IF NOT EXISTS ranking_geral (
  id SERIAL PRIMARY KEY,
  id_piloto INTEGER NOT NULL UNIQUE REFERENCES pilotos(id) ON DELETE CASCADE,
  vitorias INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS admins (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255) NOT NULL UNIQUE,
  hashed_password VARCHAR(255) NOT NULL
);
"""

def create_tables():
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(sql_commands)
        conn.commit()
        print("Tabelas criadas com sucesso ou já existentes.")
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Erro ao criar tabelas: {error}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    create_tables()
