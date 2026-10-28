import os
from dotenv import load_dotenv
import requests
import pandas as pd
from sqlalchemy import text,create_engine
from sqlalchemy.engine import URL
import logging

load_dotenv()

#SQLAlchemy
DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 5432)),
    database=os.getenv("DB_NAME"),
)

conexao = create_engine(DATABASE_URL, pool_pre_ping=True)

#LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

#Request
url = 'http://127.0.0.1:8000/dados'

requisicao = requests.get(url)
texto = requisicao.json()

#Pandas
df_dados = pd.DataFrame(texto)

#Tratamento de Strings
df_dados['nome'] = df_dados['nome'].str.title().str.strip()
df_dados['email'] = df_dados['email'].str.lower().str.strip()

#Tratamento de data
df_dados['data_nascimento'] = pd.to_datetime(df_dados['data_nascimento'],format='%Y-%m-%d',errors='coerce')


#Tratamento Colunas
colunas_esperadas = ['id','nome','email','cpf','data_nascimento',]

tratamento = (
    df_dados['id'].duplicated(keep=False) |
    (df_dados['id'] < 0) |
    df_dados['nome'].isnull() |
    (df_dados['data_nascimento'] > '2024-1-1') |
    df_dados['cpf'].isnull() |
    df_dados['cpf'].duplicated(keep=False) |
    df_dados['id'].isnull() |
    (df_dados['data_nascimento'] < '1930-1-1') |
    df_dados['data_nascimento'].isnull()
)

df_dados_validos = df_dados[~tratamento]
df_dados_invalidos = df_dados[tratamento]

#Resolvendo dados invalidos
df_dados_invalidos['data_nascimento'] = df_dados_invalidos['data_nascimento'].fillna('2000-01-01')

dados_recebidos = len(df_dados)
dados_validos = len(df_dados_validos)
dados_invalidos = len(df_dados_invalidos)
porcentagem = (dados_invalidos / dados_recebidos) * 100

logging.info(f"Dados Recebidos: {dados_recebidos}")
logging.info(f"Dados Validos: {dados_validos}")
logging.info(f"Dados Inválidos: {dados_invalidos}")
logging.info(f"Porcentagem de rejeição: {porcentagem}")
if porcentagem > 10:
    logging.warning("Porcentagem de Rejeição Acima do Limite")
else:
    logging.info('Porcentagem de Rejeição Aceita')

if set(colunas_esperadas) == set(df_dados.columns):
    logging.info('Colunas esperadas aceitas!')
else:
    logging.warning('Colunas esperadas recusadas!')

#Transformando Pandas em Dicionario
df_dicionario = df_dados_validos.to_dict(orient='records')
df_dicionario_invalido = df_dados_invalidos.to_dict(orient='records')
def subindo_dados_validos():
    with conexao.begin() as conn: 
        contagem = conn.execute(
            text(
                    """
        INSERT INTO funcionario_valido(id,nome,data_nascimento,email,cpf)
        VALUES(:id,:nome,:data_nascimento,:email,:cpf)
        ON CONFLICT (id) DO UPDATE
        SET
        nome = EXCLUDED.nome,
        email = EXCLUDED.email
        WHERE
        funcionario_valido.nome IS DISTINCT FROM EXCLUDED.nome OR
        funcionario_valido.email IS DISTINCT FROM EXCLUDED.email
        """),
        df_dicionario,

)
        return contagem.rowcount  

def subindo_dados_invalidos():
    with conexao.begin() as conn: 
        conn.execute(
            text(
                    """
        INSERT INTO funcionario_invalido(id,nome,data_nascimento,email,cpf)
        VALUES(:id,:nome,:data_nascimento,:email,:cpf)
        """),
        df_dicionario_invalido,

)
def consultar_colunas():
    with conexao.begin() as conect:
        consulta = conect.execute(text("SELECT * FROM funcionario_valido"))
    return consulta.fetchall()


def nova_etapa(nome,funcao):
    logging.info(f"Iniciando etapa {nome}")
    try:
        resultado = funcao()
        logging.info(f"Etapa {nome} concluida!")
    except Exception:
        logging.exception(f"Erro na etapa {nome}")
        raise
    return resultado

def nota_etapa_invalida(nome,funcao):
    logging.info(f"Iniciando etapa {nome}")
    try:
        resultado = funcao()
        logging.info(f"Etapa {nome} concluida!")
    except Exception:
        logging.exception(f"Erro na etapa {nome}")
        raise
    return resultado

def nova_etapa_consulta(nome,funcao):
    logging.info(f"Iniciando etapa {nome}")
    try:
        resultado = funcao()
    except Exception:
        logging.exception(f"Erro na etapa {funcao}")
        raise
    return resultado
    


etapa_bd = nova_etapa('Subindo dados válidos',subindo_dados_validos)
etapa_bd_invalido = nota_etapa_invalida('Subindo dados inválidos',subindo_dados_invalidos)
etapa_bd_invalido
etapa_bd
logging.info(f"Dados da etapa Dados Validos Inseridos/Atualizados: {etapa_bd}")

print("1) Sim")
print("2) Não")
pergunta = input(str("Você gostaria de transformar os dados validos em csv?: "))
if pergunta == '1':
    etapa_consulta = nova_etapa_consulta("Transformando dados validos em csv",consultar_colunas)
    resultado = pd.DataFrame(etapa_consulta)
    transform = resultado.to_csv('dados_validos.csv',index=False)
    transform
    logging.info("Transformação feita com sucesso!")
elif pergunta == '2':
    print('Ok, fechando sistema..')
else:
    print("Não entendi o que você quis dizer")
    