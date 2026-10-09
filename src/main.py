from ingestion.db import Neo4jConnector
from ingestion.pipeline import ETLPipeline

if __name__ == "__main__":
    # 1. Valida/cria as restrições de unicidade
    db = Neo4jConnector()
    db.setup_constraints()
    db.close()

    # 2. Executa a ingestão completa
    pipeline = ETLPipeline()
    try:
        pipeline.run_all()
    finally:
        pipeline.close()