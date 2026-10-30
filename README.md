# licdGuardCollector

**licdGuardCollector** is a Python-based data collection and ingestion project focused on Brazilian **public procurement** data.

The project implements ETL (Extract, Transform, Load) pipelines to process **public procurement** datasets, including bidding processes, procurement items, participating companies, and administrative sanctions.

The collected information is structured and stored in a Neo4j graph database, enabling the exploration of relationships between public agencies, procurement processes, companies, and administrative sanctions.

## Main Objectives

- Consolidate **public procurement** information from different datasets.
- Transform CSV data into a structured graph model.
- Establish relationships between companies, public agencies, procurement processes, and administrative sanctions.
- Provide a foundation for data analysis and relationship exploration.

## Data Source

**Note:** The data used in this project is available from the **Brazilian government's open data repository** at **https://dadosabertos.compras.gov.br/**.

⚠️ **Warning:** The CSV files in the `data/` directory are **sample files only** used for validating the ingestion pipeline. For production use, ingestion must be performed with real data collected directly from the **public data source**.

## Technology Stack

- **Python 3.9+** – Data processing and ETL pipelines.
- **Neo4j** – Graph database for storing and exploring relationships.
- **Docker and Docker Compose** – Database environment management.
- **Pandas / Python libraries** – Data processing, according to project dependencies.
- **CSV** – Input data format.

## Project Structure

```text
licdGuardCollector/
├── data/
│   ├── Licitacao.csv
│   ├── ItemLicitacao.csv
│   ├── ParticipantesLicitacao.csv
│   ├── CEIS.csv
│   └── CNEP.csv
├── src/
│   └── ingestion/
│       ├── config.py
│       ├── db.py
│       ├── pipeline.py
│       └── pipeline_historico.py
├── .gitignore
├── LICENSE.md
├── docker-compose.yaml
└── requirements.txt
```

### Main Components

- `config.py`: Application configuration and environment variables.
- `db.py`: Neo4j database connection and constraint setup.
- `pipeline.py`: ETL pipeline for current procurement data.
- `pipeline_historico.py`: ETL pipeline for historical procurement data.
- `data/`: Input CSV datasets.

## Data Model

The project uses Neo4j to represent **public procurement** information as a graph.

### Nodes

| Entity | Description |
|---|---|
| `OrgaoPublico` | Public agencies responsible for procurement processes |
| `Licitacao` | **Public procurement** processes |
| `Item` | Items included in procurement processes |
| `Empresa` | Companies participating in procurement processes |
| `Sancao` | Administrative sanctions recorded in CEIS and CNEP |

### Relationships

The graph model includes the following relationships:

```text
OrgaoPublico -[:REALIZOU]-> Licitacao

Licitacao -[:TEM_ITEM]-> Item

Empresa -[:PARTICIPOU]-> Item

Empresa -[:VENCEU]-> Item

Empresa -[:SOFREU_SANCAO]-> Sancao
```

This structure enables the exploration of connections between companies, public agencies, procurement processes, items, and administrative sanctions.

## Installation

### Prerequisites

Before installing the project, make sure you have:

- Python 3.9 or later.
- pip.
- Docker.
- Docker Compose.

### 1. Clone the repository

```bash
git clone https://github.com/vshofar/licdGuardCollector.git

cd licdGuardCollector
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root directory.

Example:

```env
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=CHANGE_ME
DATA_DIR=./data
BATCH_SIZE=5000
```

Replace `CHANGE_ME` with a password of your choice.

Make sure the Neo4j credentials configured in `docker-compose.yaml` are consistent with the application configuration.

**Important:** Do not commit `.env` files, passwords, or other secrets to the repository.

### 4. Start Neo4j

Start the database using Docker Compose:

```bash
docker compose up -d
```

Check the container status:

```bash
docker compose ps
```

### 5. Access Neo4j Browser

Once Neo4j is running, access:

```text
http://localhost:7474
```

Use the username and password configured for your Neo4j instance.

## Configuration

The application uses environment variables for database connectivity and data processing configuration.

| Variable | Description | Default |
|---|---|---|
| `NEO4J_URI` | Neo4j connection URI | `bolt://127.0.0.1:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | Must be configured |
| `DATA_DIR` | Directory containing CSV input files | `./data` |
| `BATCH_SIZE` | Number of records processed per batch | `5000` |

The environment configuration should be consistent with the Neo4j Docker Compose configuration.

## Usage

The project provides two ETL pipelines.

### Current Data Pipeline

The current data pipeline processes the following datasets:

```bash
python src/ingestion/pipeline.py
```

The pipeline processes the following files:

1. `Licitacao.csv` – Procurement processes and public agencies.
2. `ItemLicitacao.csv` – Procurement items.
3. `ParticipantesLicitacao.csv` – Participating companies and winners.
4. `CEIS.csv` – CEIS administrative sanctions.
5. `CNEP.csv` – CNEP administrative sanctions.

### Historical Data Pipeline

The historical pipeline supports multiple CSV files per dataset type.

Run:

```bash
python src/ingestion/pipeline_historico.py
```

The historical pipeline includes:

- Reading multiple CSV files from the configured directory.
- Processing files in chronological order.
- Sequential ingestion of procurement processes, items, and participants.
- Retry mechanism for database deadlocks.
- Final ingestion report generation.

**Note:** The historical data directory must be configured in `pipeline_historico.py` before execution.

## CSV File Formats

The ETL pipelines expect CSV files containing the following fields.

### Licitacao.csv

| Field | Description |
|---|---|
| `Código UG` | Public agency code |
| `Nome UG` | Public agency name |
| `Número Licitação` | Procurement number |
| `Objeto` | Procurement object description |
| `Modalidade da Licitação` | Procurement modality |
| `Data Abertura` | Opening date |

### ItemLicitacao.csv

| Field | Description |
|---|---|
| `Número Licitação` | Procurement number |
| `Código UG` | Public agency code |
| `Código Item Compra` | Procurement item code |
| `Descrição` | Item description |
| `Quantidade Item` | Item quantity |
| `Valor Estimado` | Estimated value |

### ParticipantesLicitacao.csv

| Field | Description |
|---|---|
| `Número Licitação` | Procurement number |
| `Código UG` | Public agency code |
| `Código Item Compra` | Procurement item code |
| `Código Participante` | Company CNPJ |
| `Nome Participante` | Company name |
| `Flag Vencedor` | Winner indicator (YES/NO) |
| `Valor Item` | Awarded item value |

### CEIS.csv and CNEP.csv

| Field | Description |
|---|---|
| `CPF OU CNPJ DO SANCIONADO` | Sanctioned entity identifier |
| `CPF ou CNPJ do Sancionado` | CNPJ used for company relationships |
| `Fundamentação Legal` | Legal basis for the sanction |
| `Data Início Sanção` | Sanction start date |
| `Data Fim Sanção` | Sanction end date |
| `Órgão Sancionador` | Sanctioning agency |

## Technical Features

The project includes the following technical capabilities:

- **Encoding Support:** Automatic support for ISO-8859-1 and UTF-8-sig encodings.
- **Batch Processing:** Processes records in batches to optimize memory usage.
- **Retry Logic:** Automatic retry with exponential backoff for database deadlocks.
- **Database Constraints:** Unique constraints in Neo4j to help prevent duplicate records.
- **Logging:** Detailed logs of the ingestion process.
- **Historical Processing:** Sequential processing of historical procurement datasets.

## Development

### Run Tests

```bash
pytest
```

### Format Code

```bash
black src/
```

## Future Improvements

Potential areas for future development include:

- Expanding automated test coverage.
- Improving data validation and error handling.
- Enhancing ETL pipeline monitoring and reporting.
- Improving historical data processing configuration.
- Optimizing Neo4j queries and ingestion performance.
- Improving project documentation.

## License

This project is licensed under the **MIT License**.

See the [LICENSE.md](LICENSE.md) file for details.