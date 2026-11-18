import os
import sys

import pytest

from analisador.config import PASTA_BASE, PASTA_TRANSCRICOES, configurar_ffmpeg_local, pasta_downloads

so_linux = pytest.mark.skipif(os.name == "nt" or sys.platform == "darwin", reason="regra XDG é do Linux")


@so_linux
def test_pasta_downloads_le_configuracao_xdg(tmp_path):
    (tmp_path / ".config").mkdir()
    (tmp_path / ".config" / "user-dirs.dirs").write_text(
        '# comentario\nXDG_DESKTOP_DIR="$HOME/Área de Trabalho"\nXDG_DOWNLOAD_DIR="$HOME/Baixados"\n',
        encoding="utf-8")
    assert pasta_downloads(str(tmp_path)) == str(tmp_path / "Baixados")


@so_linux
def test_pasta_downloads_desativada_aponta_para_home_e_usa_padrao(tmp_path):
    (tmp_path / ".config").mkdir()
    (tmp_path / ".config" / "user-dirs.dirs").write_text('XDG_DOWNLOAD_DIR="$HOME/"\n', encoding="utf-8")
    assert pasta_downloads(str(tmp_path)) == str(tmp_path / "Downloads")


@so_linux
def test_pasta_downloads_sem_configuracao_usa_padrao(tmp_path):
    assert pasta_downloads(str(tmp_path)) == str(tmp_path / "Downloads")


def test_arquivos_ficam_dentro_da_pasta_do_app_em_downloads():
    assert os.path.basename(PASTA_BASE) == "Analisador YouTube"
    assert os.path.dirname(PASTA_TRANSCRICOES) == PASTA_BASE


def test_configura_ffmpeg_local_quando_pasta_existe(tmp_path, monkeypatch):
    pasta_bin = tmp_path / "ffmpeg" / "bin"
    pasta_bin.mkdir(parents=True)
    monkeypatch.setenv("PATH", "/usr/bin")

    assert configurar_ffmpeg_local(str(tmp_path)) is True
    assert os.environ["PATH"].split(os.pathsep)[0] == str(pasta_bin)

    configurar_ffmpeg_local(str(tmp_path))  # chamar de novo não duplica
    assert os.environ["PATH"].split(os.pathsep).count(str(pasta_bin)) == 1


def test_nao_mexe_no_path_sem_ffmpeg_local(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin")
    assert configurar_ffmpeg_local(str(tmp_path)) is False
    assert os.environ["PATH"] == "/usr/bin"
