#!/bin/sh

# Comando para verificar se o usuário 'admin' já existe no banco de dados.
# Ele tenta se conectar ao banco de dados e executar uma query simples.
python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM admins WHERE username = %s', ('admin',))
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    if count == 0:
        print('Usuário admin não encontrado. Criando agora...')
        # Se o usuário não existe, executa o script de criação
        os.system('python create_admin.py')
    else:
        print('Usuário admin já existe. Ignorando a criação.')
except Exception as e:
    print(f'Erro ao verificar o usuário admin: {e}')
"

echo "Verificando e criando as tabelas do banco de dados..."
python create_tables.py

# Inicia o servidor Uvicorn após a verificação/criação do usuário.
uvicorn main:app --host 0.0.0.0 --port $PORT
