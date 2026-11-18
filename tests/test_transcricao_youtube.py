import os
from types import SimpleNamespace

import pytest

from analisador.downloader import DownloadCancelado
from analisador.transcricao_youtube import (
    ORIGEM_AUDIO,
    ORIGEM_LEGENDA,
    TranscritorYoutube,
    escolher_legenda,
)
from analisador.transcriber import TranscricaoCancelada

URL = "https://youtu.be/dQw4w9WgXcQ"


def legenda(codigo, texto="texto da legenda", nome=None, erro=None):
    def gerar():
        if erro:
            raise erro
        return texto
    return SimpleNamespace(code=codigo, name=nome or codigo, generate_txt_captions=gerar)


# ------------------------------------------------------------ escolher_legenda

@pytest.mark.parametrize("codigos,esperado", [
    (["en", "a.pt", "pt", "pt-BR"], "pt-BR"),   # autor + idioma exato vence
    (["a.pt", "pt-PT"], "pt-PT"),               # autor (mesma língua) vence automática
    (["en", "a.pt"], "a.pt"),                   # só automática disponível
    (["en", "a.en", "es"], None),               # nada em português
    ([], None),
])
def test_escolher_legenda(codigos, esperado):
    escolhida = escolher_legenda([legenda(c) for c in codigos], "pt-BR")
    assert (escolhida.code if escolhida else None) == esperado


def test_escolher_legenda_nao_confunde_idiomas_com_mesmo_prefixo():
    assert escolher_legenda([legenda("ptx")], "pt-BR") is None


# ----------------------------------------------------------------- dublês

class DownloaderFalso:
    def __init__(self, erro=None):
        self.chamadas = []
        self.cancelado = False
        self._erro = erro

    def baixar(self, url, tipo, pasta, ao_progredir=None):
        self.chamadas.append((url, tipo, pasta))
        if self._erro:
            raise self._erro
        ao_progredir and ao_progredir(100)
        caminho = os.path.join(pasta, "audio.m4a")
        open(caminho, "wb").close()
        return caminho

    def cancelar(self):
        self.cancelado = True


class TranscritorFalso:
    def __init__(self):
        self.arquivos = []
        self.cancelado = False

    def transcrever(self, caminho, ao_progredir=None):
        assert os.path.isfile(caminho)  # o áudio temporário existe durante a transcrição
        self.arquivos.append(caminho)
        ao_progredir and ao_progredir(100)
        return "texto do audio", 2

    def cancelar(self):
        self.cancelado = True


def criar(legendas=(), downloader=None, transcritor=None, titulo="Aula 1. Intro"):
    yt = SimpleNamespace(title=titulo, captions=list(legendas))
    return TranscritorYoutube(youtube_factory=lambda url, cb: yt,
                              downloader=downloader or DownloaderFalso(),
                              transcritor=transcritor or TranscritorFalso())


# ------------------------------------------------------------------ fluxo

def test_usa_legenda_quando_existe_sem_baixar_audio():
    downloader = DownloaderFalso()
    progresso, status = [], []
    resultado = criar([legenda("a.pt", "olá mundo", "Português (gerado automaticamente)")],
                      downloader=downloader).transcrever(URL, progresso.append, status.append)
    assert resultado.origem == ORIGEM_LEGENDA
    assert resultado.texto == "olá mundo"
    assert resultado.titulo == "Aula 1. Intro"
    assert "gerado automaticamente" in resultado.detalhe
    assert downloader.chamadas == []
    assert progresso[-1] == 100


def test_sem_legenda_baixa_audio_temporario_transcreve_e_apaga():
    downloader, transcritor = DownloaderFalso(), TranscritorFalso()
    progresso = []
    resultado = criar([legenda("en")], downloader, transcritor).transcrever(URL, progresso.append)

    assert resultado.origem == ORIGEM_AUDIO
    assert resultado.texto == "texto do audio"
    assert resultado.nao_entendidos == 2
    assert len(downloader.chamadas) == 1
    assert not os.path.exists(transcritor.arquivos[0])  # pasta temporária apagada
    assert progresso == sorted(progresso) and progresso[-1] == 100


def test_desligar_legendas_forca_transcricao_do_audio():
    resultado = criar([legenda("pt")]).transcrever(URL, usar_legendas=False)
    assert resultado.origem == ORIGEM_AUDIO


@pytest.mark.parametrize("leg", [legenda("pt", texto="   "), legenda("pt", erro=RuntimeError("404"))])
def test_legenda_vazia_ou_com_erro_cai_para_o_audio(leg):
    assert criar([leg]).transcrever(URL).origem == ORIGEM_AUDIO


def test_url_invalida():
    with pytest.raises(ValueError):
        criar().transcrever("https://vimeo.com/123")


def test_cancelar_no_download_vira_transcricao_cancelada():
    with pytest.raises(TranscricaoCancelada):
        criar(downloader=DownloaderFalso(erro=DownloadCancelado())).transcrever(URL)


def test_cancelar_antes_de_comecar_e_propaga_para_as_etapas():
    downloader, transcritor = DownloaderFalso(), TranscritorFalso()
    t = criar(downloader=downloader, transcritor=transcritor)
    t.cancelar()
    assert downloader.cancelado and transcritor.cancelado
    with pytest.raises(TranscricaoCancelada):
        t.transcrever(URL)
    assert downloader.chamadas == []
