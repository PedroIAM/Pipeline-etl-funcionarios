import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 5432)),
    database=os.getenv("DB_NAME"),
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@app.get("/dados")
def listar(db: Session = Depends(get_db)):
    r = db.execute(text("SELECT id, nome, data_nascimento, email, cpf FROM dados ORDER BY id"))
    return [dict(row._mapping) for row in r]