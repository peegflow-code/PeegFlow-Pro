import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Dados extraídos da sua última atualização
user = "neondb_owner"
password_raw = "npg_F15cSdwAkjNr"
# O quote_plus garante que o SQLAlchemy não se confunda com caracteres da senha
password = urllib.parse.quote_plus(password_raw)

# Host exato conforme o seu painel do Neon (.c-3 incluído)
host = "ep-long-scene-ah1e55pi-pooler.c-3.us-east-1.aws.neon.tech"
dbname = "neondb"

# String de conexão com SSL Obrigatório
SQLALCHEMY_DATABASE_URL = f"postgresql://{user}:{password}@{host}/{dbname}?sslmode=require"

# Configuração da Engine para Nuvem (Neon)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Testa a conexão antes de usar (evita quedas)
    pool_recycle=300,    # Reinicia conexões a cada 5 minutos
    connect_args={'connect_timeout': 10}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()