import os
import io
import zipfile
import requests
import logging
from datetime import datetime

# Configuração de Logging para registrar sucessos e falhas em arquivo e no console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("coleta_licitacoes.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PORTAL_TRANSPARENCIA_URL = "https://portaldatransparencia.gov.br/download-de-dados/licitacoes"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0"
}


def baixar_e_extrair_licitacao_mes(ano: int, mes: int, output_dir: str = DATA_DIR) -> bool:
    """
    Baixa e extrai o CSV de Licitações para um ano e mês específicos.
    Retorna True se for bem-sucedido e False caso ocorra erro.
    """
    periodo = f"{ano}{mes:02d}"
    url = f"{PORTAL_TRANSPARENCIA_URL}/{periodo}"

    logging.info(f"➜ [Início] Processando período: {periodo}...")
    logging.info(f"URL: {url}")

    try:
        response = requests.get(url, headers=HEADERS, stream=True, timeout=60)

        # Lança exceção para status 4xx ou 5xx
        response.raise_for_status()

        # Tenta abrir o conteúdo baixado como um arquivo ZIP
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            target_csv = None
            for filename in z.namelist():
                filename_lower = filename.lower()
                if "licitacao" in filename_lower and "item" not in filename_lower and filename.endswith(".csv"):
                    target_csv = filename
                    break

            if not target_csv:
                # Fallback: busca qualquer CSV que não seja de item
                candidates = [f for f in z.namelist() if f.endswith(".csv") and "item" not in f.lower()]
                if candidates:
                    target_csv = candidates[0]

            if not target_csv:
                logging.warning(f"⚠️ [Alerta] Nenhum arquivo CSV de licitação encontrado no ZIP do período {periodo}.")
                return False

            # Extrai o arquivo selecionado
            z.extract(target_csv, path=output_dir)

            extracted_path = os.path.join(output_dir, target_csv)
            # Salva nomeando com o período para não sobrescrever (ex: Licitacao_201301.csv)
            final_path = os.path.join(output_dir, f"Licitacao_{periodo}.csv")

            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(extracted_path, final_path)

            logging.info(f"✓ [Sucesso] Período {periodo} baixado e salvo em: {final_path}")
            return True

    except requests.exceptions.HTTPError as err_http:
        status_code = err_http.response.status_code if err_http.response else "Desconhecido"
        logging.error(
            f"❌ [Erro HTTP {status_code}] Falha ao baixar período {periodo}. O arquivo pode não existir no Portal.")
    except requests.exceptions.RequestException as err_req:
        logging.error(f"❌ [Erro de Conexão] Falha na requisição para o período {periodo}: {err_req}")
    except zipfile.BadZipFile:
        logging.error(f"❌ [Erro de Arquivo] O conteúdo retornado para o período {periodo} não é um arquivo ZIP válido.")
    except Exception as err_gen:
        logging.error(f"❌ [Erro Inesperado] Erro ao processar o período {periodo}: {err_gen}")

    return False


def executar_coleta_historica(ano_inicio: int, ano_fim: int):
    """
    Itera entre os anos e meses do intervalo informado, tratando exceções individualmente.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    logging.info(f"=== Iniciando Coleta Histórica de Licitações ({ano_inicio} a {ano_fim}) ===")

    total_processados = 0
    total_sucesso = 0
    total_falhas = 0

    for ano in range(ano_inicio, ano_fim + 1):
        for mes in range(1, 13):
            total_processados += 1
            sucesso = baixar_e_extrair_licitacao_mes(ano, mes)

            if sucesso:
                total_sucesso += 1
            else:
                total_falhas += 1

    logging.info("=== Resumo do Processamento ===")
    logging.info(f"Total de meses iterados: {total_processados}")
    logging.info(f"Downloads bem-sucedidos: {total_sucesso}")
    logging.info(f"Falhas/Não encontrados: {total_falhas}")
    logging.info(f"Verifique o arquivo 'coleta_licitacoes.log' para conferir os detalhes.")


if __name__ == "__main__":
    # Coleta para os anos de 2013 e 2014
    executar_coleta_historica(ano_inicio=2013, ano_fim=2014)