# licidGuardCollector

Projeto Python para coleta e ingestão de dados de licitações públicas em banco de dados Neo4j. O projeto realiza ETL (Extract, Transform, Load) de arquivos CSV contendo informações sobre licitações, itens, participantes e sanções de empresas.

## 📋 Estrutura do Projeto

```
licidGuardCollector/
├── data/                          # Diretório para arquivos CSV de entrada
│   ├── Licitacao.csv
│   ├── ItemLicitacao.csv
│   ├── ParticipantesLicitacao.csv
│   ├── CEIS.csv
│   └── CNEP.csv
├── src/
│   └── ingestion/
│       ├── config.py             # Configurações e variáveis de ambiente
│       ├── db.py                 # Conector Neo4j e setup de constraints
│       ├── pipeline.py           # Pipeline ETL para dados atuais
│       └── pipeline_historico.py # Pipeline ETL para dados históricos
├── docker-compose.yaml           # Configuração do Neo4j via Docker
├── requirements.txt              # Dependências Python
└── .env                          # Variáveis de ambiente (não versionado)
```

## 🗄️ Modelo de Dados

O projeto utiliza Neo4j para armazenar dados em formato de grafo com as seguintes entidades:

- **OrgaoPublico**: Órgãos públicos que realizam licitações
- **Licitacao**: Licitações públicas
- **Item**: Itens das licitações
- **Empresa**: Empresas participantes das licitações
- **Sancao**: Sanções aplicadas a empresas (CEIS e CNEP)

**Relacionamentos**:
- `OrgaoPublico -[:REALIZOU]-> Licitacao`
- `Licitacao -[:TEM_ITEM]-> Item`
- `Empresa -[:PARTICIPOU]-> Item`
- `Empresa -[:VENCEU]-> Item`
- `Empresa -[:SOFREU_SANCAO]-> Sancao`

## 🚀 Instalação

### Pré-requisitos

- Docker e Docker Compose
- Python 3.9+
- pip

### Passos

1. Clone o repositório:
```bash
git clone <repository-url>
cd licidGuardCollector
```

2. Instale as dependências Python:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

4. Inicie o Neo4j com Docker Compose:
```bash
docker-compose up -d
```

5. Acesse o Neo4j Browser em `http://localhost:7474` (usuário: `neo4j`, senha: `password`)

## ⚙️ Configuração

Variáveis de ambiente disponíveis no arquivo `.env`:

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `NEO4J_URI` | URI de conexão Neo4j | `bolt://127.0.0.1:7687` |
| `NEO4J_USER` | Usuário Neo4j | `neo4j` |
| `NEO4J_PASSWORD` | Senha Neo4j | `password` |
| `DATA_DIR` | Diretório dos arquivos CSV | `./data` |
| `BATCH_SIZE` | Tamanho do lote para ingestão | `5000` |

## 📝 Uso

### Pipeline de Dados Atuais

Para processar arquivos CSV de dados atuais:

```bash
python src/ingestion/pipeline.py
```

Este pipeline processa os seguintes arquivos (em ordem):
1. `Licitacao.csv` - Licitações e órgãos públicos
2. `ItemLicitacao.csv` - Itens das licitações
3. `ParticipantesLicitacao.csv` - Participantes e vencedores
4. `CEIS.csv` - Sanções CEIS
5. `CNEP.csv` - Sanções CNEP

### Pipeline de Dados Históricos

Para processar arquivos CSV históricos (múltiplos arquivos por tipo):

```bash
python src/ingestion/pipeline_historico.py
```

Este pipeline:
- Lê múltiplos arquivos CSV do diretório configurado
- Processa em ordem cronológica
- Executa ingestão sequencial estrita: licitações → itens → participantes
- Inclui mecanismo de retry para deadlocks
- Gera relatório final de ingestão

**Nota**: O diretório de dados históricos deve ser configurado em `pipeline_historico.py` (linha 12).

## 📊 Formato dos Arquivos CSV

### Licitacao.csv
- `Código UG`: Código do órgão público
- `Nome UG`: Nome do órgão público
- `Número Licitação`: Número da licitação
- `Objeto`: Descrição do objeto
- `Modalidade da Licitação`: Modalidade
- `Data Abertura`: Data de abertura

### ItemLicitacao.csv
- `Número Licitação`: Número da licitação
- `Código UG`: Código do órgão
- `Código Item Compra`: Código do item
- `Descrição`: Descrição do item
- `Quantidade Item`: Quantidade
- `Valor Estimado`: Valor estimado

### ParticipantesLicitacao.csv
- `Número Licitação`: Número da licitação
- `Código UG`: Código do órgão
- `Código Item Compra`: Código do item
- `Código Participante`: CNPJ da empresa
- `Nome Participante`: Razão social
- `Flag Vencedor`: Indicador de vencedor (SIM/NÃO)
- `Valor Item`: Valor homologado

### CEIS.csv / CNEP.csv
- `CPF OU CNPJ DO SANCIONADO`: Identificador
- `CPF ou CNPJ do Sancionado`: CNPJ para relacionamento
- `Fundamentação Legal`: Motivo da sanção
- `Data Início Sanção`: Data início
- `Data Fim Sanção`: Data fim
- `Órgão Sancionador`: Órgão que aplicou a sanção

## 🔧 Recursos Técnicos

- **Encoding**: Suporte automático para ISO-8859-1 e UTF-8-sig
- **Batch Processing**: Processamento em lotes para otimizar memória
- **Retry Logic**: Retry automático com backoff exponencial para deadlocks
- **Constraints**: Constraints únicas em Neo4j para evitar duplicatas
- **Logging**: Logs detalhados do processo de ingestão

## 🛠️ Desenvolvimento

### Executar testes
```bash
pytest
```

### Formatar código
```bash
black src/
```

## 📄 Licença

[Adicionar informações de licença]
