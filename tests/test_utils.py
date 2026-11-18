from datetime import datetime

import pytest

from analisador.utils import (
    calcular_percentual,
    e_url_youtube_valida,
    extrair_urls,
    garantir_pasta,
    nome_arquivo_transcricao,
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
    assert nome_arquivo_transcricao("/x/aula 01.mp3", agora) == "aula 01_2026-11-18_14-30-00.txt"


def test_nome_arquivo_transcricao_remove_caracteres_invalidos_e_trata_vazio():
    agora = datetime(2026, 1, 1)
    assert nome_arquivo_transcricao('a:b*c?.wav', agora) == "a_b_c__2026-01-01_00-00-00.txt"
    assert nome_arquivo_transcricao("", agora) == "transcricao_2026-01-01_00-00-00.txt"
    assert nome_arquivo_transcricao("/pasta/***.mp3", agora) == "__2026-01-01_00-00-00.txt"


def test_garantir_pasta_cria_e_e_idempotente(tmp_path):
    destino = tmp_path / "a" / "b"
    assert garantir_pasta(str(destino)) == str(destino)
    assert destino.is_dir()
    garantir_pasta(str(destino))  # não deve falhar se já existir
