# licdGuardCollector

A Python-based ETL pipeline for collecting and processing Brazilian public procurement data and building a graph database in Neo4j.

## Data Source

The pipeline processes CSV datasets obtained from the Brazilian government's open data repository.

**Source:** [Brazilian Government Open Data Portal](https://dadosabertos.compras.gov.br/)

Input files must be downloaded separately and stored in the directories configured through `DATA_DIR` and `HISTORIC_DATA_DIR`.

## Technology Stack

- Python
- Neo4j
- Docker Compose
- Pandas
- python-dotenv
- tqdm
- CSV

## Project Structure

```text
licdGuardCollector/
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

## Installation

Clone the repository:

```bash
git clone https://github.com/vshofar/licdGuardCollector.git
cd licdGuardCollector
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```env
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=CHANGE_ME

DATA_DIR=/path/to/external/current/data
HISTORIC_DATA_DIR=/path/to/external/historical/data

BATCH_SIZE=5000
```

The data directories must be located outside the repository.

The Neo4j credentials configured in `.env` must match those defined in `docker-compose.yaml`.

Do not commit credentials or other sensitive information.

### Environment Variables

| Variable | Description |
|---|---|
| `NEO4J_URI` | Neo4j connection URI |
| `NEO4J_USER` | Neo4j username |
| `NEO4J_PASSWORD` | Neo4j password |
| `DATA_DIR` | Directory containing CSV files for the current pipeline |
| `HISTORIC_DATA_DIR` | Directory containing historical CSV files |
| `BATCH_SIZE` | Number of records processed per batch |

## Neo4j

Start the Neo4j service:

```bash
docker compose up -d
```

Check the service status:

```bash
docker compose ps
```

Access Neo4j Browser at:

http://localhost:7474

## Data Ingestion

### Current Data Pipeline

Run the current data ingestion pipeline:

```bash
python src/ingestion/pipeline.py
```

The pipeline processes the following CSV files:

- `Licitacao.csv`
- `ItemLicitacao.csv`
- `ParticipantesLicitacao.csv`
- `CEIS.csv`
- `CNEP.csv`

The files must be available in the directory configured through `DATA_DIR`.

### Historical Data Pipeline

Run the historical ingestion pipeline:

```bash
python src/ingestion/pipeline_historico.py
```

The historical data directory is configured through the `HISTORIC_DATA_DIR` environment variable.

The historical pipeline processes multiple CSV files in chronological order, performs sequential ingestion, supports retries, and generates an ingestion report.

## Data Model

The project represents procurement-related entities and their relationships in Neo4j.

## Technical Features

- CSV-based data ingestion.
- Batch processing.
- Neo4j graph database integration.
- Current and historical data ingestion pipelines.
- Environment-based configuration.
- Historical ingestion reporting.

## Development

Automated unit tests are not currently available.

Install Black:

```bash
pip install black
```

Format the source code:

```bash
black src/
```

## Future Improvements

- Implement automated unit and integration tests.
- Add data validation and improved error handling.
- Implement monitoring and ingestion reports.
- Improve historical ingestion configuration.
- Optimize Neo4j queries and data model performance.
- Enhance graph schema to track the source document associated with each graph entity.

## License

This project is licensed under the MIT License.

See the [LICENSE.md](LICENSE.md) file for details.