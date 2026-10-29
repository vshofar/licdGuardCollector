# licidGuardCollector

Python project for collecting and ingesting public procurement data into a Neo4j database. The project performs ETL (Extract, Transform, Load) of CSV files containing information about procurement processes, items, participants, and company sanctions.

## 📋 Project Structure

```
licidGuardCollector/
├── data/                          # Directory for input CSV files
│   ├── Licitacao.csv
│   ├── ItemLicitacao.csv
│   ├── ParticipantesLicitacao.csv
│   ├── CEIS.csv
│   └── CNEP.csv
├── src/
│   └── ingestion/
│       ├── config.py             # Configuration and environment variables
│       ├── db.py                 # Neo4j connector and constraint setup
│       ├── pipeline.py           # ETL pipeline for current data
│       └── pipeline_historico.py # ETL pipeline for historical data
├── docker-compose.yaml           # Neo4j configuration via Docker
├── requirements.txt              # Python dependencies
└── .env                          # Environment variables (not versioned)
```

## 🗄️ Data Model

The project uses Neo4j to store data in graph format with the following entities:

- **OrgaoPublico**: Public agencies that conduct procurement processes
- **Licitacao**: Public procurement processes
- **Item**: Procurement items
- **Empresa**: Companies participating in procurement processes
- **Sancao**: Sanctions applied to companies (CEIS and CNEP)

**Relationships**:
- `OrgaoPublico -[:REALIZOU]-> Licitacao`
- `Licitacao -[:TEM_ITEM]-> Item`
- `Empresa -[:PARTICIPOU]-> Item`
- `Empresa -[:VENCEU]-> Item`
- `Empresa -[:SOFREU_SANCAO]-> Sancao`

## 🚀 Installation

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- pip

### Steps

1. Clone the repository:
```bash
git clone <repository-url>
cd licidGuardCollector
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit the .env file with your settings
```

4. Start Neo4j with Docker Compose:
```bash
docker-compose up -d
```

5. Access Neo4j Browser at `http://localhost:7474` (username: `neo4j`, password: `password`)

## ⚙️ Configuration

Environment variables available in the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `NEO4J_URI` | Neo4j connection URI | `bolt://127.0.0.1:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `password` |
| `DATA_DIR` | Directory for CSV files | `./data` |
| `BATCH_SIZE` | Batch size for ingestion | `5000` |

## 📝 Usage

### Current Data Pipeline

To process current data CSV files:

```bash
python src/ingestion/pipeline.py
```

This pipeline processes the following files (in order):
1. `Licitacao.csv` - Procurement processes and public agencies
2. `ItemLicitacao.csv` - Procurement items
3. `ParticipantesLicitacao.csv` - Participants and winners
4. `CEIS.csv` - CEIS sanctions
5. `CNEP.csv` - CNEP sanctions

### Historical Data Pipeline

To process historical CSV files (multiple files per type):

```bash
python src/ingestion/pipeline_historico.py
```

This pipeline:
- Reads multiple CSV files from the configured directory
- Processes in chronological order
- Executes strict sequential ingestion: procurement → items → participants
- Includes retry mechanism for deadlocks
- Generates final ingestion report

**Note**: The historical data directory must be configured in `pipeline_historico.py` (line 12).

## 📊 CSV File Format

### Licitacao.csv
- `Código UG`: Public agency code
- `Nome UG`: Public agency name
- `Número Licitação`: Procurement number
- `Objeto`: Object description
- `Modalidade da Licitação`: Procurement modality
- `Data Abertura`: Opening date

### ItemLicitacao.csv
- `Número Licitação`: Procurement number
- `Código UG`: Agency code
- `Código Item Compra`: Item code
- `Descrição`: Item description
- `Quantidade Item`: Quantity
- `Valor Estimado`: Estimated value

### ParticipantesLicitacao.csv
- `Número Licitação`: Procurement number
- `Código UG`: Agency code
- `Código Item Compra`: Item code
- `Código Participante`: Company CNPJ
- `Nome Participante`: Company name
- `Flag Vencedor`: Winner indicator (YES/NO)
- `Valor Item`: Homologated value

### CEIS.csv / CNEP.csv
- `CPF OU CNPJ DO SANCIONADO`: Identifier
- `CPF ou CNPJ do Sancionado`: CNPJ for relationship
- `Fundamentação Legal`: Sanction reason
- `Data Início Sanção`: Start date
- `Data Fim Sanção`: End date
- `Órgão Sancionador`: Sanctioning agency

## 🔧 Technical Features

- **Encoding**: Automatic support for ISO-8859-1 and UTF-8-sig
- **Batch Processing**: Batch processing to optimize memory
- **Retry Logic**: Automatic retry with exponential backoff for deadlocks
- **Constraints**: Unique constraints in Neo4j to avoid duplicates
- **Logging**: Detailed logs of the ingestion process

## 🛠️ Development

### Run tests
```bash
pytest
```

### Format code
```bash
black src/
```

## 📄 License

[Add license information]
