# Arquivo: create_admin.py
import os
import psycopg2
from passlib.context import CryptContext
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Configuração do hash de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed_password = pwd_context.hash("admin")  # Altere esta senha!

# Conexão e inserção no banco de dados
try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Verifica se o usuário já existe para evitar erros
    cur.execute("SELECT COUNT(*) FROM admins WHERE username = %s;", ("admin",))
    count = cur.fetchone()[0]

    if count == 0:
        cur.execute(
            "INSERT INTO admins (username, hashed_password) VALUES (%s, %s);",
            ("admin", hashed_password)
        )
        conn.commit()
        print("Usuário 'admin' criado com sucesso!")
    else:
        print("Usuário 'admin' já existe. Nenhuma ação necessária.")

except psycopg2.Error as e:
    print(f"Erro ao inserir o usuário: {e}")
    conn.rollback()
    
finally:
    if cur:
        cur.close()
    if conn:
        conn.close()
