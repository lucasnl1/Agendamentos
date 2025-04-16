import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def connect_db():
    """Estabelece uma conexão segura com o banco de dados."""
    try:
        return psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
        )
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return None

def criar_tabela():
    """Cria a tabela de agendamentos caso não exista."""
    with connect_db() as conn:
        if conn is None:
            print("❌ Não foi possível conectar ao banco para criar a tabela.")
            return

        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agendamentos (
                id SERIAL PRIMARY KEY,
                cpf VARCHAR(11) NOT NULL,
                nome VARCHAR(255) NOT NULL,
                servico VARCHAR(255) NOT NULL,
                data DATE NOT NULL,
                hora TIME NOT NULL,
                status VARCHAR(50) DEFAULT 'Aberto',
                CONSTRAINT unique_data_hora UNIQUE (data, hora)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    usuario VARCHAR(255) UNIQUE NOT NULL,
                    senha VARCHAR(255) NOT NULL
                )
            """)
            
            conn.commit()
    print("✅ Tabela 'agendamentos' verificada/criada com sucesso!")
