from types import SimpleNamespace

import pytest

from analisador.downloader import TIPO_AUDIO, TIPO_VIDEO, DownloadCancelado, Downloader

URL = "https://youtu.be/dQw4w9WgXcQ"


class StreamFalso:
    """Simula um stream da pytubefix chamando o callback de progresso em 4 pedaços."""

    def __init__(self, callback, pasta_parcial=None, filesize=400):
        self.filesize = filesize
        self._callback = callback
        self._pasta_parcial = pasta_parcial

    def download(self, output_path):
        caminho = f"{output_path}/arquivo.mp4"
        with open(caminho, "wb") as f:
            for restante in (300, 200, 100, 0):
                f.write(b"x" * 100)
                self._callback(self, b"", restante)
        return caminho

    def get_file_path(self, output_path):
        return f"{output_path}/arquivo.mp4"


def fabrica(streams_disponiveis=True, filesize=400, chamadas=None):
    def _criar(url, callback):
        if chamadas is not None:
            chamadas.append(url)
        if url.endswith("falha00"):
            raise RuntimeError("vídeo privado")
        stream = StreamFalso(callback, filesize=filesize) if streams_disponiveis else None
        return SimpleNamespace(streams=SimpleNamespace(
            get_highest_resolution=lambda: stream,
            get_audio_only=lambda: stream,
        ))
    return _criar


@pytest.mark.parametrize("tipo", [TIPO_VIDEO, TIPO_AUDIO])
def test_baixar_reporta_progresso_e_retorna_caminho(tmp_path, tipo):
    progresso = []
    caminho = Downloader(fabrica()).baixar(URL, tipo, str(tmp_path / "saida"), progresso.append)
    assert caminho.endswith("arquivo.mp4")
    assert progresso == [25.0, 50.0, 75.0, 100.0]


def test_baixar_rejeita_url_invalida_e_tipo_desconhecido(tmp_path):
    d = Downloader(fabrica())
    with pytest.raises(ValueError):
        d.baixar("https://vimeo.com/1", TIPO_VIDEO, str(tmp_path))
    with pytest.raises(ValueError):
        d.baixar(URL, "playlist", str(tmp_path))


def test_baixar_sem_stream_disponivel(tmp_path):
    with pytest.raises(RuntimeError):
        Downloader(fabrica(streams_disponiveis=False)).baixar(URL, TIPO_VIDEO, str(tmp_path))


def test_filesize_zero_nao_divide_por_zero(tmp_path):
    progresso = []
    Downloader(fabrica(filesize=0)).baixar(URL, TIPO_VIDEO, str(tmp_path), progresso.append)
    assert progresso == [0.0, 0.0, 0.0, 0.0]


def test_cancelar_durante_download_interrompe_e_apaga_parcial(tmp_path):
    d = Downloader(fabrica())

    def ao_progredir(p):
        if p >= 50:
            d.cancelar()

    with pytest.raises(DownloadCancelado):
        d.baixar(URL, TIPO_VIDEO, str(tmp_path), ao_progredir)
    assert not (tmp_path / "arquivo.mp4").exists()


def test_baixar_varios_continua_apos_falha_e_reporta(tmp_path):
    urls = [URL, "https://youtu.be/falha00", "https://youtu.be/outro12"]
    itens = []
    baixados, falhas = Downloader(fabrica()).baixar_varios(
        urls, TIPO_AUDIO, str(tmp_path), ao_iniciar_item=lambda i, t, u: itens.append((i, t)))
    assert len(baixados) == 2
    assert falhas == [("https://youtu.be/falha00", "vídeo privado")]
    assert itens == [(1, 3), (2, 3), (3, 3)]


def test_baixar_varios_para_ao_cancelar(tmp_path):
    chamadas = []
    d = Downloader(fabrica(chamadas=chamadas))
    d.cancelar()
    with pytest.raises(DownloadCancelado):
        d.baixar_varios([URL, URL], TIPO_VIDEO, str(tmp_path))
    assert chamadas == []
