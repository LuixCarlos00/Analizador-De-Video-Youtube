import os

import pytest

from analisador.lote_transcricao import (
    TIPO_ARQUIVO,
    TIPO_LINK,
    ItemTranscricao,
    TranscritorEmLote,
)
from analisador.transcricao_youtube import ORIGEM_LEGENDA, ResultadoTranscricao
from analisador.transcriber import ErroServicoTranscricao, TranscricaoCancelada
from analisador.utils import caminho_sem_conflito

LINK = ItemTranscricao(TIPO_LINK, "https://youtu.be/dQw4w9WgXcQ")


class YoutubeFalso:
    instancias = []

    def __init__(self, idioma, respostas):
        self.respostas = respostas
        self.cancelado = False
        YoutubeFalso.instancias.append(self)

    def transcrever(self, url, ao_progredir=None, ao_status=None, usar_legendas=True):
        resposta = self.respostas[url]
        if isinstance(resposta, Exception):
            raise resposta
        ao_status and ao_status("Lendo a legenda... ")
        ao_progredir and ao_progredir(100)
        return ResultadoTranscricao(titulo=resposta[0], texto=resposta[1], origem=ORIGEM_LEGENDA)

    def cancelar(self):
        self.cancelado = True


class ArquivoFalso:
    def __init__(self, idioma):
        self.cancelado = False

    def transcrever(self, caminho, ao_progredir=None):
        return f"texto de {os.path.basename(caminho)}", 1

    def cancelar(self):
        self.cancelado = True


def criar(tmp_path, respostas=None):
    respostas = respostas or {LINK.valor: ("Aula 1", "olá")}
    return TranscritorEmLote(
        str(tmp_path / "saida"),
        criar_transcritor_youtube=lambda idioma: YoutubeFalso(idioma, respostas),
        criar_transcritor_arquivo=ArquivoFalso)


def test_item_rotulo():
    assert ItemTranscricao(TIPO_ARQUIVO, "/a/b/aula.mp3").rotulo == "[arquivo]  aula.mp3"
    assert LINK.rotulo.startswith("[YouTube]  https://")


def test_transcreve_links_e_arquivos_e_salva_cada_um(tmp_path):
    itens = [LINK, ItemTranscricao(TIPO_ARQUIVO, "/x/reuniao.mp3")]
    iniciados = []
    sucessos, falhas = criar(tmp_path).transcrever(
        itens, ao_iniciar_item=lambda i, t, item: iniciados.append((i, t)))

    assert falhas == []
    assert iniciados == [(1, 2), (2, 2)]
    assert [s.resultado.titulo for s in sucessos] == ["Aula 1", "reuniao"]
    assert sucessos[1].resultado.nao_entendidos == 1
    for s in sucessos:
        with open(s.arquivo_txt, encoding="utf-8") as f:
            assert f.read() == s.resultado.texto


def test_titulos_repetidos_nao_se_sobrescrevem(tmp_path):
    respostas = {"https://youtu.be/aaaaaaa": ("Mesmo", "a"), "https://youtu.be/bbbbbbb": ("Mesmo", "b")}
    itens = [ItemTranscricao(TIPO_LINK, u) for u in respostas]
    sucessos, _ = criar(tmp_path, respostas).transcrever(itens)
    assert len({s.arquivo_txt for s in sucessos}) == 2


def test_falha_num_item_nao_para_os_outros(tmp_path):
    respostas = {
        "https://youtu.be/aaaaaaa": ErroServicoTranscricao("sem internet"),
        "https://youtu.be/bbbbbbb": ("Vazio", "   "),
        "https://youtu.be/ccccccc": ("Ok", "texto"),
    }
    itens = [ItemTranscricao(TIPO_LINK, u) for u in respostas]
    sucessos, falhas = criar(tmp_path, respostas).transcrever(itens)
    assert [s.resultado.titulo for s in sucessos] == ["Ok"]
    assert [(f[0].valor[-7:], f[1]) for f in falhas] == [
        ("aaaaaaa", "sem internet"), ("bbbbbbb", "Nenhuma fala foi reconhecida.")]


def test_cancelar_propaga_para_o_item_atual_e_para_o_lote(tmp_path):
    YoutubeFalso.instancias.clear()
    lote = criar(tmp_path)

    def ao_status(_texto):
        lote.cancelar()  # usuário clica em Cancelar no meio do primeiro item

    with pytest.raises(TranscricaoCancelada):
        lote.transcrever([LINK, LINK], ao_status=ao_status)
    assert YoutubeFalso.instancias[0].cancelado
    assert len(YoutubeFalso.instancias) == 1  # o segundo item nem começou


def test_caminho_sem_conflito(tmp_path):
    assert caminho_sem_conflito(str(tmp_path), "a.txt") == str(tmp_path / "a.txt")
    (tmp_path / "a.txt").touch()
    (tmp_path / "a (2).txt").touch()
    assert caminho_sem_conflito(str(tmp_path), "a.txt") == str(tmp_path / "a (3).txt")
