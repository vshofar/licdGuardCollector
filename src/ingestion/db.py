from neo4j import GraphDatabase
import logging
from ingestion.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class Neo4jConnector:
    def __init__(self):
        logging.info(f"Conectando ao Neo4j - URI: {NEO4J_URI}, User: {NEO4J_USER}")
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        logging.info("Conexão com Neo4j estabelecida com sucesso!")

    def close(self):
        self.driver.close()

    def execute_query(self, query: str, parameters: dict = None):

        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return list(result)

    def setup_constraints(self):

        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (o:OrgaoPublico) REQUIRE o.codigo_ug IS UNIQUE;",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (l:Licitacao) REQUIRE l.id_compra IS UNIQUE;",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Item) REQUIRE i.id_item IS UNIQUE;",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Empresa) REQUIRE e.cnpj IS UNIQUE;",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Sancao) REQUIRE s.id_sancao IS UNIQUE;"
        ]
        logging.info("Criando restrições e índices no Neo4j...")
        for query in constraints:
            self.execute_query(query)
        logging.info("Índices e restrições criados com sucesso!")