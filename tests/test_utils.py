from datetime import datetime

import pytest

from analisador.utils import (
    calcular_percentual,
    e_url_youtube_valida,
    extrair_urls,
    garantir_pasta,
    mensagem_de_erro_amigavel,
    nome_arquivo_transcricao,
    nome_base_do_arquivo,
)


@pytest.mark.parametrize("url", [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "http://youtube.com/watch?v=dQw4w9WgXcQ&t=10s",
    "https://www.youtube.com/watch?list=PL123&v=dQw4w9WgXcQ",
    "youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/shorts/abcDEF12345",
    "  https://youtu.be/dQw4w9WgXcQ  ",
])
def test_url_valida(url):
    assert e_url_youtube_valida(url)


@pytest.mark.parametrize("url", [
    "", None, "   ", "abc",
    "https://vimeo.com/123456",
    "https://www.youtube.com/",
    "https://www.youtube.com/channel/UC123",
    "https://youtube.com.malicioso.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/",
])
def test_url_invalida(url):
    assert not e_url_youtube_valida(url)


def test_extrair_urls_aceita_virgula_quebra_de_linha_e_remove_duplicados():
    texto = "https://youtu.be/aaaaaaa, https://youtu.be/bbbbbbb\nhttps://youtu.be/aaaaaaa;;  \n"
    assert extrair_urls(texto) == ["https://youtu.be/aaaaaaa", "https://youtu.be/bbbbbbb"]


@pytest.mark.parametrize("texto", ["", None, " , \n ; "])
def test_extrair_urls_vazio(texto):
    assert extrair_urls(texto) == []


@pytest.mark.parametrize("processado,total,esperado", [
    (50, 100, 50.0), (0, 100, 0.0), (100, 100, 100.0),
    (150, 100, 100.0), (-5, 100, 0.0), (10, 0, 0.0), (10, None, 0.0),
])
def test_calcular_percentual(processado, total, esperado):
    assert calcular_percentual(processado, total) == esperado


def test_nome_arquivo_transcricao_usa_nome_de_origem_e_data():
    agora = datetime(2026, 11, 18, 14, 30, 0)
    assert nome_arquivo_transcricao("aula 01", agora) == "aula 01_2026-11-18_14-30-00.txt"


def test_nome_arquivo_transcricao_preserva_ponto_no_titulo_do_video():
    agora = datetime(2026, 1, 1)
    assert nome_arquivo_transcricao("Aula 1. Introdução", agora) == "Aula 1. Introdução_2026-01-01_00-00-00.txt"


def test_nome_arquivo_transcricao_remove_caracteres_invalidos_e_trata_vazio():
    agora = datetime(2026, 1, 1)
    assert nome_arquivo_transcricao("a:b*c?", agora) == "a_b_c__2026-01-01_00-00-00.txt"
    assert nome_arquivo_transcricao("", agora) == "transcricao_2026-01-01_00-00-00.txt"
    assert nome_arquivo_transcricao(None, agora) == "transcricao_2026-01-01_00-00-00.txt"
    assert nome_arquivo_transcricao("Quem é? / Parte 2", agora) == "Quem é_ _ Parte 2_2026-01-01_00-00-00.txt"


def test_nome_arquivo_transcricao_limita_titulos_longos():
    nome = nome_arquivo_transcricao("x" * 300, datetime(2026, 1, 1))
    assert nome == "x" * 80 + "_2026-01-01_00-00-00.txt"


def test_nome_base_do_arquivo():
    assert nome_base_do_arquivo("/x/aula 01.mp3") == "aula 01"
    assert nome_base_do_arquivo("C:/Users/a/minha.aula.m4a") == "minha.aula"


def test_mensagem_amigavel_bloqueio_de_politica_do_windows():
    erro = OSError(22, "Uma política de controle de aplicativo bloqueou este arquivo")
    erro.winerror = 4551  # atributo que o Windows preenche em OSError
    mensagem = mensagem_de_erro_amigavel(erro)
    assert "bloqueou um programa auxiliar" in mensagem
    assert "Detalhe técnico" in mensagem


def test_mensagem_amigavel_ffmpeg_ausente():
    mensagem = mensagem_de_erro_amigavel(FileNotFoundError(2, "No such file", "ffprobe"))
    assert mensagem.startswith("O ffmpeg não foi encontrado")


class VideoUnavailable(Exception):
    """Imita a hierarquia de exceções da pytubefix (comparada pelo nome da classe)."""


class VideoPrivate(VideoUnavailable):
    pass


class VideoRemovedByUploader(VideoUnavailable):
    pass


@pytest.mark.parametrize("erro,esperado", [
    (VideoUnavailable("xxxxxxxxxxx is unavailable"), "não existe ou não está disponível"),
    (VideoPrivate("abc is private"), "é privado"),  # específica vence a classe-mãe
    (VideoRemovedByUploader("abc"), "foi removido"),
])
def test_mensagem_amigavel_traduz_erros_do_youtube(erro, esperado):
    assert esperado in mensagem_de_erro_amigavel(erro)


def test_mensagem_amigavel_outros_erros_mantem_texto_original():
    assert mensagem_de_erro_amigavel(RuntimeError("vídeo privado")) == "vídeo privado"
    # FileNotFoundError de outro arquivo não deve ser confundido com ffmpeg ausente
    assert mensagem_de_erro_amigavel(FileNotFoundError("audio.mp3")) == "audio.mp3"


def test_garantir_pasta_cria_e_e_idempotente(tmp_path):
    destino = tmp_path / "a" / "b"
    assert garantir_pasta(str(destino)) == str(destino)
    assert destino.is_dir()
    garantir_pasta(str(destino))  # não deve falhar se já existir
