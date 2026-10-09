import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Garante o caminho absoluto correto para a pasta data/ na raiz do projeto
DATA_DIR = os.getenv("DATA_DIR")
if not DATA_DIR or DATA_DIR == "./data":
    DATA_DIR = str(BASE_DIR / "data")

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5000"))