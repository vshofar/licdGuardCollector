import os
import re
import time
import pandas as pd
import logging
from neo4j.exceptions import TransientError
from ingestion.db import Neo4jConnector
from ingestion.config import BATCH_SIZE

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

HISTORIC_DATA_DIR = "/home/vbatista/estudo/agentes/licdGuard/collect/licitacao"


class ETLPipelineHistoricoSequencial:
    def __init__(self, max_retries: int = 5):
        self.max_retries = max_retries
        # Setup inicial das constraints em uma conexão temporária
        db = Neo4jConnector()
        db.setup_constraints()
        db.close()

    def execute_query_with_retry(self, db: Neo4jConnector, cypher_query: str, parameters: dict):
        """Executa a query e faz retry automático caso ocorra Deadlock ou erro transitório."""
        for attempt in range(1, self.max_retries + 1):
            try:
                db.execute_query(cypher_query, parameters)
                return True
            except TransientError as e:
                if attempt == self.max_retries:
                    logging.error(f"Excedido limite de retries ({self.max_retries}) por Deadlock. Erro: {e}")
                    raise e
                sleep_time = (2 ** (attempt - 1)) * 0.2
                logging.warning(
                    f"Deadlock/TransientError detectado. Tentativa {attempt}/{self.max_retries}. "
                    f"Aguardando {sleep_time:.2f}s antes de tentar novamente..."
                )
                time.sleep(sleep_time)
            except Exception as e:
                raise e

    def process_csv_in_chunks(self, db: Neo4jConnector, filepath: str, cypher_query: str) -> tuple:
        """Lê um arquivo CSV em chunks e executa a query Cypher com contadores de registros."""
        if not os.path.exists(filepath):
            logging.warning(f"Arquivo não encontrado: {filepath}. Pulando...")
            return 0, 0

        logging.info(f"Processando arquivo: {os.path.basename(filepath)}")

        encoding = "iso-8859-1"
        try:
            chunks = pd.read_csv(filepath, sep=";", encoding=encoding, chunksize=BATCH_SIZE, dtype=str)
            _ = next(chunks)
            chunks = pd.read_csv(filepath, sep=";", encoding=encoding, chunksize=BATCH_SIZE, dtype=str)
        except (UnicodeDecodeError, Exception):
            encoding = "utf-8-sig"
            chunks = pd.read_csv(filepath, sep=";", encoding=encoding, chunksize=BATCH_SIZE, dtype=str)

        total_registros_arquivo = 0
        falhas_registros_arquivo = 0

        for chunk in chunks:
            chunk = chunk.fillna("")
            records = chunk.to_dict(orient="records")
            num_records = len(records)
            total_registros_arquivo += num_records

            try:
                self.execute_query_with_retry(db, cypher_query, {"batch": records})
            except Exception as e:
                logging.error(f"Falha ao inserir lote do arquivo {os.path.basename(filepath)}: {e}")
                falhas_registros_arquivo += num_records

        return total_registros_arquivo, falhas_registros_arquivo

    def get_arquivos_por_tipo(self):
        """Retorna dicionário com listas de arquivos separados por tipo em ordem cronológica."""
        csv_files = [f for f in os.listdir(HISTORIC_DATA_DIR) if f.endswith('.csv')]

        licitacoes = []
        itens = []
        participantes = []

        for arquivo in sorted(csv_files):
            caminho_completo = os.path.join(HISTORIC_DATA_DIR, arquivo)
            if re.search(r'_Licitação\.csv$', arquivo) and 'Item' not in arquivo and 'Participantes' not in arquivo:
                licitacoes.append(caminho_completo)
            elif re.search(r'_ItemLicitação\.csv$', arquivo):
                itens.append(caminho_completo)
            elif re.search(r'_ParticipantesLicitação\.csv$', arquivo):
                participantes.append(caminho_completo)

        return {
            "licitacao": licitacoes,
            "item_licitacao": itens,
            "participante_licitacao": participantes
        }

    def load_licitacao(self, db: Neo4jConnector, filepath: str) -> tuple:
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
        return self.process_csv_in_chunks(db, filepath, query)

    def load_item_licitacao(self, db: Neo4jConnector, filepath: str) -> tuple:
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
        return self.process_csv_in_chunks(db, filepath, query)

    def load_participante_licitacao(self, db: Neo4jConnector, filepath: str) -> tuple:
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
        return self.process_csv_in_chunks(db, filepath, query)

    def processar_lista_arquivos(self, db: Neo4jConnector, arquivos: list, tipo_nome: str, load_func) -> dict:
        """Processa sequencialmente uma lista de arquivos de um determinado tipo."""
        logging.info(
            f"=== Iniciando processamento sequencial da entidade: {tipo_nome.upper()} ({len(arquivos)} arquivos) ===")

        total_tipo = 0
        falhas_tipo = 0

        for filepath in arquivos:
            try:
                tot, falhas = load_func(db, filepath)
                total_tipo += tot
                falhas_tipo += falhas
            except Exception as e:
                logging.error(f"Erro ao processar o arquivo {os.path.basename(filepath)}: {e}")

        sucessos_tipo = total_tipo - falhas_tipo
        logging.info(
            f"=== Concluído tipo {tipo_nome.upper()} | "
            f"Total lidos: {total_tipo} | "
            f"Sucessos: {sucessos_tipo} | "
            f"Falhas: {falhas_tipo} ==="
        )
        return {"total": total_tipo, "sucessos": sucessos_tipo, "falhas": falhas_tipo}

    def run_all(self):
        """Executa a ingestão sequencial estrita: licitacao -> item_licitacao -> participante_licitacao."""
        logging.info("Iniciando Pipeline de Ingestão Histórica Sequencial por Tipo...")

        arquivos_por_tipo = self.get_arquivos_por_tipo()

        totais_globais = {
            "total_registros": 0,
            "total_sucessos": 0,
            "total_falhas": 0,
        }

        # Instancia uma única conexão com o banco para todo o ciclo de execução
        db = Neo4jConnector()
        try:
            # 1. Inserir Licitações
            res_licitacao = self.processar_lista_arquivos(
                db, arquivos_por_tipo["licitacao"], "licitacao", self.load_licitacao
            )
            totais_globais["total_registros"] += res_licitacao["total"]
            totais_globais["total_sucessos"] += res_licitacao["sucessos"]
            totais_globais["total_falhas"] += res_licitacao["falhas"]

            # 2. Inserir Itens de Licitação
            res_item = self.processar_lista_arquivos(
                db, arquivos_por_tipo["item_licitacao"], "item licitacao", self.load_item_licitacao
            )
            totais_globais["total_registros"] += res_item["total"]
            totais_globais["total_sucessos"] += res_item["sucessos"]
            totais_globais["total_falhas"] += res_item["falhas"]

            # 3. Inserir Participantes de Licitação
            res_participante = self.processar_lista_arquivos(
                db, arquivos_por_tipo["participante_licitacao"], "participante licitacao",
                self.load_participante_licitacao
            )
            totais_globais["total_registros"] += res_participante["total"]
            totais_globais["total_sucessos"] += res_participante["sucessos"]
            totais_globais["total_falhas"] += res_participante["falhas"]

        finally:
            db.close()

        # Relatório Final Consolidado
        logging.info("==================================================")
        logging.info("          RELATÓRIO FINAL DE INGESTÃO             ")
        logging.info("==================================================")
        logging.info(f"Total de registros lidos      : {totais_globais['total_registros']}")
        logging.info(f"Total de inserções com SUCESSO : {totais_globais['total_sucessos']}")
        logging.info(f"Total de inserções NÃO feitas : {totais_globais['total_falhas']}")
        if totais_globais['total_registros'] > 0:
            taxa_sucesso = (totais_globais['total_sucessos'] / totais_globais['total_registros']) * 100
            logging.info(f"Taxa de sucesso               : {taxa_sucesso:.2f}%")
        logging.info("==================================================")


if __name__ == "__main__":
    pipeline = ETLPipelineHistoricoSequencial(max_retries=5)
    pipeline.run_all()