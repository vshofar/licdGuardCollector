from src.db import Neo4jConnector

if __name__ == "__main__":
    print("Iniciando teste de conexão e criação de restrições...")
    db = Neo4jConnector()
    db.setup_constraints()
    db.close()
    print("✅ Teste concluído com sucesso!")