import os

from analisador.config import configurar_ffmpeg_local


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
