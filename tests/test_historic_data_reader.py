"""
Testes unitários do componente HistoricDataReader.

Cenários marcados como "COMPORTAMENTO ATUAL" documentam o funcionamento
herdado da pipeline original, que talvez não seja o desejado. Se esse
comportamento for corrigido, esses testes devem ser atualizados.
"""
import importlib
import logging
import unicodedata
from unittest.mock import Mock, call

import pytest
from pandas.errors import EmptyDataError

import ingestion.historic_data_reader as hdr
from ingestion.historic_data_reader import HistoricDataReader


# --------------------------------------------------------------------------- #
# Fixtures e helpers
# --------------------------------------------------------------------------- #
def escrever_csv(caminho, conteudo: str, encoding: str = "iso-8859-1"):
    caminho.write_bytes(conteudo.encode(encoding))
    return str(caminho)


@pytest.fixture
def reader(tmp_path):
    return HistoricDataReader(data_dir=str(tmp_path), batch_size=2)


@pytest.fixture
def modulo_com_config_do_ambiente(monkeypatch, tmp_path):
    """
    Recarrega config e historic_data_reader com variáveis de ambiente
    controladas, pois os valores padrão de __init__ são resolvidos na
    importação do módulo. Ao final, restaura o ambiente e recarrega de novo.
    """
    from ingestion import config

    monkeypatch.setenv("HISTORIC_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BATCH_SIZE", "123")
    importlib.reload(config)
    importlib.reload(hdr)

    yield hdr

    monkeypatch.undo()
    importlib.reload(config)
    importlib.reload(hdr)


# --------------------------------------------------------------------------- #
# __init__
# --------------------------------------------------------------------------- #
class TestInit:
    def test_parametros_validos_sao_armazenados(self, tmp_path):
        reader = HistoricDataReader(data_dir=str(tmp_path), batch_size=10)

        assert reader.data_dir == str(tmp_path)
        assert reader.batch_size == 10

    def test_sem_parametros_usa_valores_do_config(self, modulo_com_config_do_ambiente, tmp_path):
        reader = modulo_com_config_do_ambiente.HistoricDataReader()

        assert reader.data_dir == str(tmp_path)
        assert reader.batch_size == 123

    @pytest.mark.parametrize("data_dir", ["", None], ids=["vazio", "none"])
    def test_data_dir_ausente_lanca_value_error(self, data_dir):
        with pytest.raises(ValueError, match="HISTORIC_DATA_DIR não está configurado"):
            HistoricDataReader(data_dir=data_dir)

    def test_diretorio_inexistente_nao_lanca_erro(self, tmp_path):
        inexistente = str(tmp_path / "nao_existe")

        reader = HistoricDataReader(data_dir=inexistente)

        assert reader.data_dir == inexistente


# --------------------------------------------------------------------------- #
# listar_arquivos_por_tipo
# --------------------------------------------------------------------------- #
class TestListarArquivosPorTipo:
    def test_classifica_os_tres_tipos(self, tmp_path, reader):
        for nome in ["202301_Licitação.csv", "202301_ItemLicitação.csv", "202301_ParticipantesLicitação.csv"]:
            (tmp_path / nome).touch()

        resultado = reader.listar_arquivos_por_tipo()

        assert resultado == {
            "licitacao": [str(tmp_path / "202301_Licitação.csv")],
            "item_licitacao": [str(tmp_path / "202301_ItemLicitação.csv")],
            "participante_licitacao": [str(tmp_path / "202301_ParticipantesLicitação.csv")],
        }

    def test_diretorio_vazio_retorna_tres_listas_vazias(self, reader):
        assert reader.listar_arquivos_por_tipo() == {
            "licitacao": [],
            "item_licitacao": [],
            "participante_licitacao": [],
        }

    def test_ignora_arquivos_que_nao_sao_csv(self, tmp_path, reader):
        for nome in ["202301_Licitação.txt", "202301_Licitação.xlsx", "202301_Licitação.csv.bak"]:
            (tmp_path / nome).touch()

        resultado = reader.listar_arquivos_por_tipo()

        assert all(lista == [] for lista in resultado.values())

    @pytest.mark.parametrize("nome", ["dados.csv", "Licitacao.csv", "202301_Licitacao.csv", "Licitação.csv"])
    def test_ignora_csv_fora_do_padrao_de_nome(self, tmp_path, reader, nome):
        (tmp_path / nome).touch()

        resultado = reader.listar_arquivos_por_tipo()

        assert all(lista == [] for lista in resultado.values())

    def test_retorna_arquivos_em_ordem_crescente(self, tmp_path, reader, monkeypatch):
        # listdir simulado para garantir entrada fora de ordem, independente do sistema de arquivos
        monkeypatch.setattr(
            hdr.os, "listdir",
            lambda _: ["202312_Licitação.csv", "202206_Licitação.csv", "202301_Licitação.csv"],
        )

        resultado = reader.listar_arquivos_por_tipo()

        assert resultado["licitacao"] == [
            str(tmp_path / "202206_Licitação.csv"),
            str(tmp_path / "202301_Licitação.csv"),
            str(tmp_path / "202312_Licitação.csv"),
        ]

    def test_retorna_caminho_completo(self, tmp_path, reader):
        (tmp_path / "202301_Licitação.csv").touch()

        caminho = reader.listar_arquivos_por_tipo()["licitacao"][0]

        assert caminho == str(tmp_path / "202301_Licitação.csv")

    def test_extensao_maiuscula_nao_e_listada(self, tmp_path, reader):
        # COMPORTAMENTO ATUAL: endswith('.csv') diferencia maiúsculas de minúsculas
        (tmp_path / "202301_Licitação.CSV").touch()

        assert reader.listar_arquivos_por_tipo()["licitacao"] == []

    def test_nome_com_acentos_nfd_nao_e_reconhecido(self, reader, monkeypatch):
        # COMPORTAMENTO ATUAL: o regex usa "ç"/"ã" compostos (NFC); nomes em NFD
        # (comuns em arquivos vindos do macOS) não são reconhecidos
        nome_nfd = unicodedata.normalize("NFD", "202301_Licitação.csv")
        assert nome_nfd != "202301_Licitação.csv"
        monkeypatch.setattr(hdr.os, "listdir", lambda _: [nome_nfd])

        assert reader.listar_arquivos_por_tipo()["licitacao"] == []

    def test_diretorio_inexistente_lanca_file_not_found(self, tmp_path):
        reader = HistoricDataReader(data_dir=str(tmp_path / "nao_existe"))

        with pytest.raises(FileNotFoundError):
            reader.listar_arquivos_por_tipo()


# --------------------------------------------------------------------------- #
# ler_csv_em_chunks
# --------------------------------------------------------------------------- #
class TestLerCsvEmChunks:
    def test_leitura_basica_iso_8859_1(self, tmp_path, reader):
        arquivo = escrever_csv(tmp_path / "a.csv", "Código UG;Nome UG\n10;Órgão A\n")

        assert list(reader.ler_csv_em_chunks(arquivo)) == [[{"Código UG": "10", "Nome UG": "Órgão A"}]]

    def test_divide_em_chunks_de_batch_size(self, tmp_path, reader):
        linhas = "\n".join(str(i) for i in range(1, 6))
        arquivo = escrever_csv(tmp_path / "a.csv", f"id\n{linhas}\n")

        chunks = list(reader.ler_csv_em_chunks(arquivo))

        assert [len(c) for c in chunks] == [2, 2, 1]
        assert [r["id"] for c in chunks for r in c] == ["1", "2", "3", "4", "5"]

    def test_mantem_zeros_a_esquerda_como_string(self, tmp_path, reader):
        arquivo = escrever_csv(tmp_path / "a.csv", "Código UG;CNPJ\n000123;00012345000199\n")

        registro = next(reader.ler_csv_em_chunks(arquivo))[0]

        assert registro == {"Código UG": "000123", "CNPJ": "00012345000199"}

    def test_celula_vazia_vira_string_vazia(self, tmp_path, reader):
        arquivo = escrever_csv(tmp_path / "a.csv", "A;B\n1;\n")

        registro = next(reader.ler_csv_em_chunks(arquivo))[0]

        assert registro == {"A": "1", "B": ""}

    def test_acentos_em_iso_8859_1_sao_lidos_corretamente(self, tmp_path, reader):
        arquivo = escrever_csv(
            tmp_path / "a.csv",
            "Número Licitação;Descrição\n1;Aquisição de câmeras\n",
            encoding="iso-8859-1",
        )

        registro = next(reader.ler_csv_em_chunks(arquivo))[0]

        assert registro == {"Número Licitação": "1", "Descrição": "Aquisição de câmeras"}

    def test_campo_entre_aspas_com_separador_e_um_unico_campo(self, tmp_path, reader):
        arquivo = escrever_csv(tmp_path / "a.csv", 'Objeto;Valor\n"Compra; com ponto e vírgula";10\n')

        registro = next(reader.ler_csv_em_chunks(arquivo))[0]

        assert registro == {"Objeto": "Compra; com ponto e vírgula", "Valor": "10"}

    def test_arquivo_inexistente_nao_gera_itens_e_loga_warning(self, tmp_path, reader, caplog):
        inexistente = str(tmp_path / "nao_existe.csv")

        with caplog.at_level(logging.WARNING):
            resultado = list(reader.ler_csv_em_chunks(inexistente))

        assert resultado == []
        assert any(
            r.levelno == logging.WARNING and inexistente in r.getMessage() for r in caplog.records
        )

    def test_criar_generator_sem_iterar_nao_le_arquivo_nem_loga(self, tmp_path, reader, caplog, monkeypatch):
        arquivo = escrever_csv(tmp_path / "a.csv", "A\n1\n")
        read_csv = Mock()
        monkeypatch.setattr(hdr.pd, "read_csv", read_csv)

        with caplog.at_level(logging.DEBUG):
            reader.ler_csv_em_chunks(arquivo)

        read_csv.assert_not_called()
        assert caplog.records == []

    def test_iterar_arquivo_valido_loga_info_com_nome_do_arquivo(self, tmp_path, reader, caplog):
        arquivo = escrever_csv(tmp_path / "202301_Licitação.csv", "A\n1\n")

        with caplog.at_level(logging.INFO):
            list(reader.ler_csv_em_chunks(arquivo))

        assert any(
            r.levelno == logging.INFO and "202301_Licitação.csv" in r.getMessage() for r in caplog.records
        )

    def test_arquivo_vazio_lanca_empty_data_error(self, tmp_path, reader):
        arquivo = escrever_csv(tmp_path / "a.csv", "")

        with pytest.raises(EmptyDataError):
            list(reader.ler_csv_em_chunks(arquivo))

    def test_arquivo_so_com_cabecalho_gera_um_chunk_vazio(self, tmp_path, reader):
        # COMPORTAMENTO ATUAL: gera [[]] em vez de um generator vazio
        arquivo = escrever_csv(tmp_path / "a.csv", "A;B\n")

        assert list(reader.ler_csv_em_chunks(arquivo)) == [[]]

    def test_arquivo_utf8_e_lido_com_dados_corrompidos(self, tmp_path, reader):
        # COMPORTAMENTO ATUAL (pendente de decisão): iso-8859-1 decodifica
        # qualquer byte, então o fallback para utf-8-sig nunca é acionado
        arquivo = escrever_csv(tmp_path / "a.csv", "Número;Nome\n1;Ação\n", encoding="utf-8")

        registro = next(reader.ler_csv_em_chunks(arquivo))[0]

        assert registro == {"NÃºmero": "1", "Nome": "AÃ§Ã£o"}

    def test_arquivo_utf8_com_bom_mantem_prefixo_na_primeira_coluna(self, tmp_path, reader):
        # COMPORTAMENTO ATUAL (pendente de decisão): o BOM não é removido
        arquivo = escrever_csv(tmp_path / "a.csv", "Número;Nome\n1;Ação\n", encoding="utf-8-sig")

        registro = next(reader.ler_csv_em_chunks(arquivo))[0]

        assert registro == {"ï»¿NÃºmero": "1", "Nome": "AÃ§Ã£o"}


# --------------------------------------------------------------------------- #
# _abrir_csv_com_fallback_encoding
# --------------------------------------------------------------------------- #
def _chamada_esperada(caminho, encoding, batch_size):
    return call(caminho, sep=";", encoding=encoding, chunksize=batch_size, dtype=str)


def _gerador_com_erro_de_decodificacao():
    raise UnicodeDecodeError("iso-8859-1", b"\xff", 0, 1, "erro simulado")
    yield  # torna a função um generator


class TestAbrirCsvComFallbackEncoding:
    CAMINHO = "/qualquer/arquivo.csv"

    def test_leitura_normal_usa_iso_8859_1_com_parametros_corretos(self, monkeypatch):
        reader = HistoricDataReader(data_dir="/qualquer", batch_size=7)
        leitor_final = Mock(name="leitor_final")
        read_csv = Mock(side_effect=[iter(["primeiro_chunk"]), leitor_final])
        monkeypatch.setattr(hdr.pd, "read_csv", read_csv)

        resultado = reader._abrir_csv_com_fallback_encoding(self.CAMINHO)

        assert resultado is leitor_final
        assert read_csv.call_args_list == [
            _chamada_esperada(self.CAMINHO, "iso-8859-1", 7),
            _chamada_esperada(self.CAMINHO, "iso-8859-1", 7),
        ]

    @pytest.mark.parametrize(
        "primeira_leitura",
        [ValueError("falha ao abrir"), _gerador_com_erro_de_decodificacao()],
        ids=["erro_ao_abrir", "erro_ao_ler_primeiro_chunk"],
    )
    def test_primeira_leitura_falha_refaz_com_utf8_sig(self, monkeypatch, primeira_leitura):
        reader = HistoricDataReader(data_dir="/qualquer", batch_size=7)
        leitor_fallback = Mock(name="leitor_fallback")
        read_csv = Mock(side_effect=[primeira_leitura, leitor_fallback])
        monkeypatch.setattr(hdr.pd, "read_csv", read_csv)

        resultado = reader._abrir_csv_com_fallback_encoding(self.CAMINHO)

        assert resultado is leitor_fallback
        assert read_csv.call_args_list[-1] == _chamada_esperada(self.CAMINHO, "utf-8-sig", 7)

    def test_ambas_leituras_falham_propaga_excecao(self, monkeypatch):
        reader = HistoricDataReader(data_dir="/qualquer", batch_size=7)
        read_csv = Mock(side_effect=[ValueError("falha iso"), ValueError("falha utf8")])
        monkeypatch.setattr(hdr.pd, "read_csv", read_csv)

        with pytest.raises(ValueError, match="falha utf8"):
            reader._abrir_csv_com_fallback_encoding(self.CAMINHO)
