from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
import psycopg2
from dotenv import load_dotenv
import os
from pydantic import BaseModel
from datetime import date
from fastapi.middleware.cors import CORSMiddleware
from auth import get_current_user, Token, create_access_token, verify_password, pwd_context, get_db_connection
from datetime import timedelta

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Cria a instância do FastAPI
app = FastAPI()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4200")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Modelos de Dados ---
class Piloto(BaseModel):
    nome: str
    equipe: str
    foto: str | None = None

class Corrida(BaseModel):
    nome: str
    data_corrida: date

class Voto(BaseModel):
    id_corrida: int
    id_piloto: int

# --- ROTAS PÚBLICAS (sem autenticação) ---

@app.get("/")
def read_root():
    return {"Bem-vindo": "API Cabaço Of The Day!"}

@app.get("/pilotos")
def listar_pilotos():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id, nome, equipe, foto FROM pilotos;")
        pilotos_db = cur.fetchall()
        
        pilotos = []
        for piloto_db in pilotos_db:
            pilotos.append({
                "id": piloto_db[0],
                "nome": piloto_db[1],
                "equipe": piloto_db[2],
                "foto": piloto_db[3]
            })
            
        cur.close()
        return pilotos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@app.get("/corridas")
def listar_corridas():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Altere o SQL para incluir a nova coluna
        cur.execute("SELECT id, nome, data_corrida, votacao_fechada FROM corridas ORDER BY data_corrida DESC;")
        corridas_db = cur.fetchall()
        
        corridas = []
        for corrida_db in corridas_db:
            corridas.append({
                "id": corrida_db[0],
                "nome": corrida_db[1],
                "data_corrida": corrida_db[2],
                "votacao_fechada": corrida_db[3] # Adicione esta linha
            })

        cur.close()
        return corridas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@app.post("/votar")
def votar(voto: Voto, request: Request):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Primeiro, verifique se a votação está fechada
        cur.execute("SELECT votacao_fechada FROM corridas WHERE id = %s;", (voto.id_corrida,))
        corrida_status = cur.fetchone()
        
        if corrida_status and corrida_status[0] == True:
            raise HTTPException(status_code=400, detail="A votação para esta corrida já foi encerrada.")

        # Se a votação estiver aberta, continue com a lógica de voto
        ip_usuario = request.client.host
        cur.execute(
            "INSERT INTO votos (id_corrida, id_piloto, ip_usuario) VALUES (%s, %s, %s);",
            (voto.id_corrida, voto.id_piloto, ip_usuario)
        )
        
        conn.commit()
        cur.close()
        
        return {"mensagem": "Voto registrado com sucesso!"}
    
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=409, detail="Você já votou nesta corrida.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@app.get("/resultados/{corrida_id}")
def obter_resultados(corrida_id: int):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT 
                p.nome, 
                p.equipe, 
                p.foto, 
                COUNT(v.id) AS total_votos,
                (COUNT(v.id) * 100.0 / (SELECT COUNT(*) FROM votos WHERE id_corrida = %s)) AS porcentagem
            FROM votos v
            JOIN pilotos p ON v.id_piloto = p.id
            WHERE v.id_corrida = %s
            GROUP BY p.nome, p.equipe, p.foto
            ORDER BY total_votos DESC;
            """,
            (corrida_id, corrida_id)
        )
        resultados_db = cur.fetchall()
        
        resultados = []
        for resultado_db in resultados_db:
            resultados.append({
                "nome": resultado_db[0],
                "equipe": resultado_db[1],
                "foto": resultado_db[2],
                "votos": resultado_db[3],
                "porcentagem": round(resultado_db[4], 2) # Arredonda para 2 casas decimais
            })

        cur.close()
        return resultados
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@app.get("/ranking-geral")
def obter_ranking_geral():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT p.nome, p.equipe, p.foto, r.vitorias 
            FROM ranking_geral r
            JOIN pilotos p ON r.id_piloto = p.id
            ORDER BY r.vitorias DESC, p.nome ASC;
            """
        )
        ranking_db = cur.fetchall()
        
        ranking = []
        for rank_db in ranking_db:
            ranking.append({
                "nome": rank_db[0],
                "equipe": rank_db[1],
                "foto": rank_db[2],
                "vitorias": rank_db[3]
            })

        cur.close()
        return ranking
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

# --- ROTAS DE ADMIN (protegidas) ---
@app.post("/token", response_model=Token)
def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT hashed_password FROM admins WHERE username = %s;", (form_data.username,))
        user_db = cur.fetchone()
        cur.close()
        
        if not user_db or not verify_password(form_data.password, user_db[0]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário ou senha inválidos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": form_data.username}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

# Rotas de Pilotos
@app.post("/admin/pilotos")
def adicionar_piloto(piloto: Piloto, current_user: Annotated[dict, Depends(get_current_user)]):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO pilotos (nome, equipe, foto) VALUES (%s, %s, %s) RETURNING id;",
            (piloto.nome, piloto.equipe, piloto.foto)
        )
        
        piloto_id = cur.fetchone()[0]
        
        conn.commit()
        cur.close()
        
        return {"id": piloto_id, **piloto.dict()}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@app.put("/admin/pilotos/{piloto_id}")
def atualizar_piloto(piloto_id: int, piloto: Piloto, current_user: Annotated[dict, Depends(get_current_user)]):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "UPDATE pilotos SET nome = %s, equipe = %s, foto = %s WHERE id = %s;",
            (piloto.nome, piloto.equipe, piloto.foto, piloto_id)
        )

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Piloto não encontrado")

        conn.commit()
        cur.close()

        return {"mensagem": "Piloto atualizado com sucesso"}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@app.delete("/admin/pilotos/{piloto_id}")
def deletar_piloto(piloto_id: int, current_user: Annotated[dict, Depends(get_current_user)]):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM pilotos WHERE id = %s;", (piloto_id,))
        
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Piloto não encontrado")
        
        conn.commit()
        cur.close()
        
        return {"mensagem": "Piloto deletado com sucesso"}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

# Rotas de Corridas
@app.post("/admin/corridas")
def adicionar_corrida(corrida: Corrida, current_user: Annotated[dict, Depends(get_current_user)]):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO corridas (nome, data_corrida) VALUES (%s, %s) RETURNING id;",
            (corrida.nome, corrida.data_corrida)
        )
        
        corrida_id = cur.fetchone()[0]
        
        conn.commit()
        cur.close()
        
        return {"id": corrida_id, **corrida.dict()}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@app.put("/admin/corridas/{corrida_id}")
def atualizar_corrida(corrida_id: int, corrida: Corrida, current_user: Annotated[dict, Depends(get_current_user)]):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "UPDATE corridas SET nome = %s, data_corrida = %s WHERE id = %s;",
            (corrida.nome, corrida.data_corrida, corrida_id)
        )
        
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Corrida não encontrada")
        
        conn.commit()
        cur.close()
        
        return {"mensagem": "Corrida atualizada com sucesso"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@app.delete("/admin/corridas/{corrida_id}")
def deletar_corrida(corrida_id: int, current_user: Annotated[dict, Depends(get_current_user)]):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM votos WHERE id_corrida = %s;", (corrida_id,))
        cur.execute("DELETE FROM corridas WHERE id = %s;", (corrida_id,))
        
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Corrida não encontrada")
        
        conn.commit()
        cur.close()
        
        return {"mensagem": "Corrida e votos associados deletados com sucesso"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@app.put("/admin/corridas/{corrida_id}/fechar-votacao")
def fechar_votacao(corrida_id: int, current_user: Annotated[dict, Depends(get_current_user)]):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Atualiza o status da corrida para "fechada"
        cur.execute(
            "UPDATE corridas SET votacao_fechada = TRUE WHERE id = %s;",
            (corrida_id,)
        )
        
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Corrida não encontrada")

        # 2. Encontra o piloto com mais votos (o "Cabaço do Dia")
        cur.execute(
            """
            SELECT id_piloto FROM votos
            WHERE id_corrida = %s
            GROUP BY id_piloto
            ORDER BY COUNT(id) DESC
            LIMIT 1;
            """,
            (corrida_id,)
        )
        vencedor_db = cur.fetchone()

        if vencedor_db:
            id_piloto_vencedor = vencedor_db[0]
            
            # 3. Atualiza o ranking geral
            # Tenta dar um UPDATE (se o piloto já existir)
            cur.execute(
                """
                UPDATE ranking_geral 
                SET vitorias = vitorias + 1 
                WHERE id_piloto = %s;
                """,
                (id_piloto_vencedor,)
            )

            # Se o piloto não existia no ranking, fazemos um INSERT
            if cur.rowcount == 0:
                cur.execute(
                    """
                    INSERT INTO ranking_geral (id_piloto, vitorias)
                    VALUES (%s, 1);
                    """,
                    (id_piloto_vencedor,)
                )

        conn.commit()
        cur.close()
        
        return {"mensagem": "Votação da corrida fechada e ranking geral atualizado com sucesso"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@app.get("/admin/me")
async def read_current_user(current_user: Annotated[dict, Depends(get_current_user)]):
    return current_user
