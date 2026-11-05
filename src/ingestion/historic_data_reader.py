import os
import re
import logging
from typing import Dict, Iterator, List

import pandas as pd

from ingestion.config import HISTORIC_DATA_DIR, BATCH_SIZE

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class HistoricDataReader:
    """
    Responsável exclusivamente por localizar e ler os arquivos de dados
    históricos disponíveis no diretório de entrada (HISTORIC_DATA_DIR),
    sem qualquer conhecimento sobre o destino dos dados (Neo4j/Cypher).
    """

    def __init__(self, data_dir: str = HISTORIC_DATA_DIR, batch_size: int = BATCH_SIZE):
        """
        :param data_dir: diretório onde estão os CSVs históricos.
                          Injetável para facilitar os testes unitários.
        :param batch_size: tamanho do chunk de leitura do CSV.
        """
        if not data_dir:
            raise ValueError(
                "HISTORIC_DATA_DIR não está configurado. "
                "Defina a variável de ambiente HISTORIC_DATA_DIR no arquivo .env"
            )
        self.data_dir = data_dir
        self.batch_size = batch_size

    def listar_arquivos_por_tipo(self) -> Dict[str, List[str]]:
        """
        Varre self.data_dir e retorna um dicionário com os caminhos completos
        dos arquivos .csv, separados por tipo e em ordem cronológica (alfabética):
            {
                "licitacao": [...],
                "item_licitacao": [...],
                "participante_licitacao": [...],
            }
        """
        csv_files = [f for f in os.listdir(self.data_dir) if f.endswith('.csv')]

        licitacoes = []
        itens = []
        participantes = []

        for arquivo in sorted(csv_files):
            caminho_completo = os.path.join(self.data_dir, arquivo)
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

    def _abrir_csv_com_fallback_encoding(self, filepath: str):
        """
        Tenta abrir o CSV com encoding 'iso-8859-1' (padrão de arquivos
        governamentais br). Caso a leitura do primeiro chunk falhe, refaz a
        leitura usando 'utf-8-sig'.
        Retorna o iterador de chunks (TextFileReader) pronto para uso.
        """
        encoding = "iso-8859-1"
        try:
            chunks = pd.read_csv(
                filepath, sep=";", encoding=encoding, chunksize=self.batch_size, dtype=str
            )
            _ = next(chunks)
            chunks = pd.read_csv(
                filepath, sep=";", encoding=encoding, chunksize=self.batch_size, dtype=str
            )
        except (UnicodeDecodeError, Exception):
            encoding = "utf-8-sig"
            chunks = pd.read_csv(
                filepath, sep=";", encoding=encoding, chunksize=self.batch_size, dtype=str
            )
        return chunks

    def ler_csv_em_chunks(self, filepath: str) -> Iterator[List[dict]]:
        """
        Generator que lê `filepath` em lotes de `self.batch_size` linhas.
        - Detecta o encoding automaticamente (iso-8859-1, com fallback para
          utf-8-sig).
        - Substitui valores NaN por "".
        - Cada item gerado (`yield`) é uma lista de dicts (orient="records"),
          pronta para ser usada, por exemplo, como parâmetro de um
          `UNWIND $batch`.
        - Se o arquivo não existir, loga um warning e o generator termina
          sem produzir nenhum item.
        """
        if not os.path.exists(filepath):
            logging.warning(f"Arquivo não encontrado: {filepath}. Pulando...")
            return

        logging.info(f"Processando arquivo: {os.path.basename(filepath)}")

        chunks = self._abrir_csv_com_fallback_encoding(filepath)

        for chunk in chunks:
            chunk = chunk.fillna("")
            records = chunk.to_dict(orient="records")
            yield records
