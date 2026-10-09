import os
import pandas as pd
import logging
from tqdm import tqdm
from src.db import Neo4jConnector
from src.config import DATA_DIR, BATCH_SIZE

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class ETLPipeline:
    def __init__(self):
        self.db = Neo4jConnector()

    def close(self):
        self.db.close()

    def process_csv_in_chunks(self, filename: str, cypher_query: str, prepare_batch_fn=None):
        """Lê um arquivo CSV em chunks e executa a query Cypher em lotes via UNWIND."""
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            logging.warning(f"Arquivo não encontrado: {filepath}. Pulando...")
            return

        logging.info(f"Processando arquivo: {filename}")

        # Tenta ler primeiro com latin-1 (padrão de arquivos br/governamentais) e fallback para utf-8-sig
        encoding = "iso-8859-1"
        try:
            chunks = pd.read_csv(filepath, sep=";", encoding=encoding, chunksize=BATCH_SIZE, dtype=str)
            first_chunk = next(chunks)  # Valida se o encoding consegue decodificar o primeiro chunk
            chunks = pd.read_csv(filepath, sep=";", encoding=encoding, chunksize=BATCH_SIZE, dtype=str)
        except (UnicodeDecodeError, Exception):
            encoding = "utf-8-sig"
            chunks = pd.read_csv(filepath, sep=";", encoding=encoding, chunksize=BATCH_SIZE, dtype=str)

        for chunk in tqdm(chunks, desc=f"Carregando {filename} ({encoding})"):
            chunk = chunk.fillna("")
            records = chunk.to_dict(orient="records")

            if prepare_batch_fn:
                records = prepare_batch_fn(records)

            self.db.execute_query(cypher_query, {"batch": records})

    # --- 1. Carga de Licitações e Órgãos Públicos ---
    def load_licitacoes(self):
        query = """
        UNWIND $batch AS row
        MERGE (o:OrgaoPublico {codigo_ug: row['Código UG']})
        ON CREATE SET o.nome_ug = row['Nome UG']

        MERGE (l:Licitacao {id_compra: row['Número Licitação'] + '_' + row['Código UG']})
        ON CREATE SET 
            l.numero = row['Número Licitação'],
            l.objeto = row['Objeto'],
            l.modalidade = row['Modalidade da Licitação'],
            l.data_abertura = row['Data Abertura']

        MERGE (o)-[:REALIZOU]->(l)
        """
        self.process_csv_in_chunks("Licitacao.csv", query)

    # --- 2. Carga dos Itens da Licitação ---
    def load_itens(self):
        query = """
        UNWIND $batch AS row
        MERGE (i:Item {id_item: row['Número Licitação'] + '_' + row['Código UG'] + '_' + row['Código Item Compra']})
        ON CREATE SET 
            i.descricao = row['Descrição'],
            i.quantidade = toInteger(row['Quantidade Item']),
            i.valor_estimado = toFloat(replace(row['Valor Estimado'], ',', '.'))

        WITH i, row
        MATCH (l:Licitacao {id_compra: row['Número Licitação'] + '_' + row['Código UG']})
        MERGE (l)-[:TEM_ITEM]->(i)
        """
        self.process_csv_in_chunks("ItemLicitacao.csv", query)


    # --- 3. Carga de Participantes e Vencedores conectando ao Item ---
    def load_participantes(self):
        query = """
        UNWIND $batch AS row
        MATCH (i:Item {id_item: row['Número Licitação'] + '_' + row['Código UG'] + '_' + row['Código Item Compra']})

        MERGE (e:Empresa {cnpj: row['Código Participante']})
        ON CREATE SET e.razao_social = row['Nome Participante']

        MERGE (e)-[:PARTICIPOU]->(i)

        WITH e, i, row
        WHERE row['Flag Vencedor'] = 'SIM'
        MERGE (e)-[v:VENCEU]->(i)
        ON CREATE SET v.valor_homologado = toFloat(replace(replace(row['Valor Item'], '.', ''), ',', '.'))
        """
        self.process_csv_in_chunks("ParticipantesLicitacao.csv", query)

    # --- 4. Carga de Sanções (CEIS e CNEP) ---
    def load_sancoes(self, filename: str, tipo_sancao: str):
        query = f"""
        UNWIND $batch AS row
        MERGE (s:Sancao {{id_sancao: '{tipo_sancao}_' + row['CPF OU CNPJ DO SANCIONADO'] + '_' + row['DATA INÍCIO SANÇÃO']}})
        ON CREATE SET 
            s.tipo = '{tipo_sancao}',
            s.motivo = row['Fundamentação Legal'],
            s.data_inicio = row['Data Início Sanção'],
            s.data_fim = row['Data Fim Sanção'],
            s.orgao_sancionador = row['Órgão Sancionador']

        WITH s, row
        MATCH (e:Empresa {{cnpj: row['CPF ou CNPJ do Sancionado']}})
        MERGE (e)-[:SOFREU_SANCAO]->(s)
        """
        self.process_csv_in_chunks(filename, query)

    def run_all(self):
        logging.info("Iniciando Pipeline de Ingestão ETL...")
        self.load_licitacoes()
        self.load_itens()
        self.load_participantes()
        self.load_sancoes("CEIS.csv", "CEIS")
        self.load_sancoes("CNEP.csv", "CNEP")
        logging.info("ETL concluído com sucesso!")