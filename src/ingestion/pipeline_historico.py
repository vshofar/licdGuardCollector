import os
import re
import pandas as pd
import logging
from tqdm import tqdm
from ingestion.db import Neo4jConnector
from ingestion.config import BATCH_SIZE

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

HISTORIC_DATA_DIR = "/home/vbatista/estudo/agentes/licdGuard/collect/licitacao"


class ETLPipelineHistorico:
    def __init__(self):
        self.db = Neo4jConnector()

    def close(self):
        self.db.close()

    def process_csv_in_chunks(self, filepath: str, cypher_query: str, prepare_batch_fn=None):
        """Lê um arquivo CSV em chunks e executa a query Cypher em lotes via UNWIND."""
        if not os.path.exists(filepath):
            logging.warning(f"Arquivo não encontrado: {filepath}. Pulando...")
            return

        logging.info(f"Processando arquivo: {os.path.basename(filepath)}")

        encoding = "iso-8859-1"
        try:
            chunks = pd.read_csv(filepath, sep=";", encoding=encoding, chunksize=BATCH_SIZE, dtype=str)
            first_chunk = next(chunks)
            chunks = pd.read_csv(filepath, sep=";", encoding=encoding, chunksize=BATCH_SIZE, dtype=str)
        except (UnicodeDecodeError, Exception):
            encoding = "utf-8-sig"
            chunks = pd.read_csv(filepath, sep=";", encoding=encoding, chunksize=BATCH_SIZE, dtype=str)

        for chunk in tqdm(chunks, desc=f"Carregando {os.path.basename(filepath)} ({encoding})"):
            chunk = chunk.fillna("")
            records = chunk.to_dict(orient="records")

            if prepare_batch_fn:
                records = prepare_batch_fn(records)

            self.db.execute_query(cypher_query, {"batch": records})

    def get_periodos_ordenados(self):
        """Retorna lista de períodos (YYYYMM) ordenados cronologicamente."""
        csv_files = [f for f in os.listdir(HISTORIC_DATA_DIR) if f.endswith('.csv')]
        periodos = set()
        
        for filename in csv_files:
            match = re.match(r'^(\d{6})_', filename)
            if match:
                periodos.add(match.group(1))
        
        return sorted(periodos)

    def get_arquivos_por_periodo(self, periodo: str):
        """Retorna os arquivos de um período específico, ordenados por tipo."""
        csv_files = [f for f in os.listdir(HISTORIC_DATA_DIR) if f.endswith('.csv') and f.startswith(periodo)]
        
        arquivos_ordenados = []
        
        for arquivo in sorted(csv_files):
            if re.search(r'_Licitação\.csv$', arquivo) and 'Item' not in arquivo and 'Participantes' not in arquivo:
                arquivos_ordenados.append(os.path.join(HISTORIC_DATA_DIR, arquivo))
        
        for arquivo in sorted(csv_files):
            if re.search(r'_ItemLicitação\.csv$', arquivo):
                arquivos_ordenados.append(os.path.join(HISTORIC_DATA_DIR, arquivo))
        
        for arquivo in sorted(csv_files):
            if re.search(r'_ParticipantesLicitação\.csv$', arquivo):
                arquivos_ordenados.append(os.path.join(HISTORIC_DATA_DIR, arquivo))
        
        return arquivos_ordenados

    def load_licitacoes_periodo(self, filepath: str):
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
        self.process_csv_in_chunks(filepath, query)

    def load_itens_periodo(self, filepath: str):
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
        self.process_csv_in_chunks(filepath, query)

    def load_participantes_periodo(self, filepath: str):
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
        self.process_csv_in_chunks(filepath, query)

    def processar_periodo(self, periodo: str):
        """Processa todos os arquivos de um período na ordem correta."""
        logging.info(f"=== Processando período {periodo} ===")
        
        arquivos = self.get_arquivos_por_periodo(periodo)
        logging.info(f"Arquivos a processar em ordem: {[os.path.basename(f) for f in arquivos]}")
        
        for arquivo in arquivos:
            nome_arquivo = os.path.basename(arquivo)
            
            if re.search(r'_Licitação\.csv$', nome_arquivo) and 'Item' not in nome_arquivo and 'Participantes' not in nome_arquivo:
                self.load_licitacoes_periodo(arquivo)
            elif re.search(r'_ItemLicitação\.csv$', nome_arquivo):
                self.load_itens_periodo(arquivo)
            elif re.search(r'_ParticipantesLicitação\.csv$', nome_arquivo):
                self.load_participantes_periodo(arquivo)
            else:
                logging.info(f"Pulando arquivo não processado: {nome_arquivo}")

    def run_all(self, periodo_inicio: str = None, periodo_fim: str = None):
        """Executa a ingestão de todos os períodos ou de um intervalo específico."""
        logging.info("Iniciando Pipeline de Ingestão Histórica...")
        
        periodos = self.get_periodos_ordenados()
        
        if periodo_inicio:
            periodos = [p for p in periodos if p >= periodo_inicio]
        if periodo_fim:
            periodos = [p for p in periodos if p <= periodo_fim]
        
        logging.info(f"Total de períodos a processar: {len(periodos)}")
        
        for periodo in periodos:
            try:
                self.processar_periodo(periodo)
            except Exception as e:
                logging.error(f"Erro ao processar período {periodo}: {e}")
                continue
        
        logging.info("Ingestão histórica concluída!")


if __name__ == "__main__":
    pipeline = ETLPipelineHistorico()
    try:
        pipeline.run_all("201301", "202412")
    finally:
        pipeline.close()
