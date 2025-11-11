from dotenv import load_dotenv
from database import DatabaseManager

# Carrega variáveis de ambiente
load_dotenv()

def test_connection():
    db = DatabaseManager()
    try:
        # Teste de conexão
        if db.test_connection():
            print('✅ Conexão PostgreSQL estabelecida com sucesso!')
        else:
            print('❌ Falha na conexão PostgreSQL!')
            return
            
        # Teste de inicialização das tabelas
        if db.init_database():
            print('✅ Tabelas criadas/verificadas com sucesso!')
        else:
            print('❌ Falha na criação das tabelas!')
            
    except Exception as e:
        print(f'❌ Erro na conexão: {e}')

if __name__ == "__main__":
    test_connection()