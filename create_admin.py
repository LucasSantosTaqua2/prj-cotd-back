# Arquivo: create_admin.py
from passlib.context import CryptContext
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed_password = pwd_context.hash("Lucas3322!") # Troque por sua senha

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute(
    "INSERT INTO admins (username, hashed_password) VALUES (%s, %s);",
    ("admin", hashed_password)
)

conn.commit()
print("Usuário 'admin' criado com sucesso!")

cur.close()
conn.close()