# Roadmap

This document describes the planned future development of **licdGuardCollector**, including the main improvement areas and estimated effort.

The roadmap focuses on improving data quality, ingestion reliability, graph modeling, traceability, and project maintainability.

## Planned Improvements

### 1. ETL Pipeline Evolution — 4 hours

- Improve pipeline modularity and code organization.
- Reduce duplicated processing logic between current and historical pipelines.
- Improve handling of different input dataset versions.

### 2. Data Validation and Error Handling — 4 hours

- Implement input data validation.
- Improve handling of missing or invalid fields.
- Provide more informative error messages.
- Improve logging of rejected or inconsistent records.

### 3. Automated Testing — 5 hours

- Introduce automated unit tests for core ingestion components.
- Add tests for data transformation and validation.
- Test database interaction and ingestion behavior.
- Establish a basic automated testing structure.

### 4. Monitoring and Ingestion Reports — 3 hours

- Improve ingestion execution reports.
- Include processed, rejected, and failed record counts.
- Improve visibility into pipeline execution time and errors.

### 5. Neo4j Data Model Optimization — 4 hours

- Review graph constraints and indexes.
- Evaluate existing relationships and node properties.
- Optimize ingestion queries and database performance.
- Review duplicate prevention strategies.

### 6. Document Provenance and Graph Traceability — 5 hours

- Enhance the graph schema to track the source document associated with each graph entity.
- Define how source document metadata will be represented.
- Establish relationships or properties linking graph entities to their source documents.
- Enable identification of the original document responsible for each ingested entity.

## Estimated Effort

| Improvement Area | Estimated Effort |
|---|---:|
| ETL Pipeline Evolution | 4 hours |
| Data Validation and Error Handling | 4 hours |
| Automated Testing | 5 hours |
| Monitoring and Ingestion Reports | 3 hours |
| Neo4j Data Model Optimization | 4 hours |
| Document Provenance and Graph Traceability | 5 hours |
| **Total** | **25 hours** |

## Notes

- The estimates represent planned development effort and may change as implementation progresses.
- Tasks may be reprioritized according to technical findings and project needs.
- This roadmap represents future work and does not imply that the listed improvements have already been implemented.
