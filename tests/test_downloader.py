import os
from types import SimpleNamespace

import pytest

from analisador.downloader import (
    TIPO_AUDIO,
    TIPO_VIDEO,
    DownloadCancelado,
    Downloader,
    escolher_stream_de_imagem,
)

URL = "https://youtu.be/dQw4w9WgXcQ"


class StreamFalso:
    """Simula um stream da pytubefix: grava o arquivo em 4 pedaços chamando o callback."""

    def __init__(self, nome, callback, filesize=400, resolution=None, video_codec=None, fps=30, erro=None):
        self.nome = nome
        self.erro = erro
        self.filesize = filesize
        self.resolution = resolution
        self.video_codec = video_codec
        self.fps = fps
        self._callback = callback

    def get_file_path(self, filename=None, output_path=None):
        return os.path.join(output_path, filename or self.nome)

    def download(self, output_path, filename=None, skip_existing=True):
        assert skip_existing is False
        caminho = self.get_file_path(filename, output_path)
        with open(caminho, "wb") as f:
            for restante in (300, 200, 100, 0):
                f.write(b"x" * 100)
                if self.erro and restante == 200:
                    raise self.erro  # falha de rede no meio do download
                self._callback(self, b"", restante)
        return caminho


def fabrica(imagens=("1080p",), progressivo=True, audio=True, chamadas=None, filesize=400, erro_audio=None):
    """Cria um youtube_factory falso com os streams pedidos."""
    def _criar(url, callback):
        if chamadas is not None:
            chamadas.append(url)
        if url.endswith("falha00"):
            raise RuntimeError("vídeo privado")
        lista_imagens = [StreamFalso(f"v{r}.mp4", callback, filesize, r, "avc1.64") for r in imagens]
        return SimpleNamespace(streams=SimpleNamespace(
            filter=lambda **kw: lista_imagens,
            get_highest_resolution=lambda: StreamFalso("Titulo 360p.mp4", callback, filesize) if progressivo else None,
            get_audio_only=lambda: StreamFalso("Titulo.m4a", callback, filesize, erro=erro_audio) if audio else None,
        ))
    return _criar


class Juntador:
    def __init__(self):
        self.chamadas = []

    def __call__(self, imagem, audio, saida):
        assert os.path.isfile(imagem) and os.path.isfile(audio)
        self.chamadas.append((os.path.basename(imagem), os.path.basename(audio), saida))
        open(saida, "wb").close()


def criar(ffmpeg=True, juntador=None, **kw):
    return Downloader(fabrica(**kw), juntar=juntador or Juntador(), ffmpeg_disponivel=lambda: ffmpeg)


# ------------------------------------------------------- escolha de qualidade

def _s(res, codec="avc1.64", fps=30):
    return SimpleNamespace(resolution=res, video_codec=codec, fps=fps)


def test_escolhe_maior_h264_ate_1080p():
    streams = [_s("2160p", "av01"), _s("1080p", "vp9"), _s("1080p"), _s("720p"), _s("1440p", "vp9")]
    escolhido = escolher_stream_de_imagem(streams)
    assert (escolhido.resolution, escolhido.video_codec) == ("1080p", "avc1.64")


def test_prefere_h264_mesmo_com_resolucao_menor():
    escolhido = escolher_stream_de_imagem([_s("1080p", "av01"), _s("720p")])
    assert escolhido.resolution == "720p"


def test_prefere_mais_quadros_por_segundo_no_empate():
    assert escolher_stream_de_imagem([_s("1080p", fps=30), _s("1080p", fps=60)]).fps == 60


@pytest.mark.parametrize("streams", [[], [_s(None)], [_s("4320p")]])
def test_sem_stream_aceitavel(streams):
    assert escolher_stream_de_imagem(streams) is None


# ------------------------------------------------------------------- áudio

def test_baixar_audio_reporta_progresso_e_retorna_caminho(tmp_path):
    progresso = []
    caminho = criar().baixar(URL, TIPO_AUDIO, str(tmp_path / "saida"), progresso.append)
    assert os.path.basename(caminho) == "Titulo.m4a"
    assert progresso == [25.0, 50.0, 75.0, 100.0]


# ------------------------------------------------------------------- vídeo

def test_video_baixa_imagem_e_audio_e_junta(tmp_path):
    juntador, progresso = Juntador(), []
    caminho = criar(juntador=juntador).baixar(URL, TIPO_VIDEO, str(tmp_path), progresso.append)

    assert caminho == str(tmp_path / "v1080p.mp4")
    assert os.path.isfile(caminho)
    assert juntador.chamadas[0][:2] == ("imagem.mp4", "audio.m4a")
    assert progresso == sorted(progresso) and progresso[-1] == 100
    assert os.listdir(tmp_path) == ["v1080p.mp4"]  # partes temporárias não ficam na pasta do usuário


def test_video_sem_ffmpeg_usa_formato_progressivo(tmp_path):
    juntador = Juntador()
    caminho = criar(ffmpeg=False, juntador=juntador).baixar(URL, TIPO_VIDEO, str(tmp_path))
    assert os.path.basename(caminho) == "Titulo 360p.mp4"
    assert juntador.chamadas == []


def test_video_sem_ffmpeg_e_sem_progressivo_explica_o_problema(tmp_path):
    with pytest.raises(RuntimeError, match="ffmpeg"):
        criar(ffmpeg=False, progressivo=False).baixar(URL, TIPO_VIDEO, str(tmp_path))


def test_video_sem_imagem_mp4_usa_progressivo(tmp_path):
    caminho = criar(imagens=()).baixar(URL, TIPO_VIDEO, str(tmp_path))
    assert os.path.basename(caminho) == "Titulo 360p.mp4"


def test_video_sem_audio(tmp_path):
    with pytest.raises(RuntimeError, match="áudio"):
        criar(audio=False).baixar(URL, TIPO_VIDEO, str(tmp_path))


# ------------------------------------------------------ validações e erros

def test_baixar_rejeita_url_invalida_e_tipo_desconhecido(tmp_path):
    d = criar()
    with pytest.raises(ValueError):
        d.baixar("https://vimeo.com/1", TIPO_VIDEO, str(tmp_path))
    with pytest.raises(ValueError):
        d.baixar(URL, "playlist", str(tmp_path))


def test_filesize_zero_nao_divide_por_zero(tmp_path):
    progresso = []
    criar(filesize=0).baixar(URL, TIPO_AUDIO, str(tmp_path), progresso.append)
    assert progresso == [0.0, 0.0, 0.0, 0.0]


@pytest.mark.parametrize("tipo", [TIPO_AUDIO, TIPO_VIDEO])
def test_cancelar_durante_download_interrompe_e_apaga_parcial(tmp_path, tipo):
    d = criar()

    def ao_progredir(p):
        if p >= 20:
            d.cancelar()

    with pytest.raises(DownloadCancelado):
        d.baixar(URL, tipo, str(tmp_path), ao_progredir)
    assert os.listdir(tmp_path) == []


def test_baixar_varios_continua_apos_falha_e_reporta(tmp_path):
    urls = [URL, "https://youtu.be/falha00", "https://youtu.be/outro12"]
    itens = []
    baixados, falhas = criar().baixar_varios(
        urls, TIPO_AUDIO, str(tmp_path), ao_iniciar_item=lambda i, t, u: itens.append((i, t)))
    assert [url for url, _ in baixados] == [URL, "https://youtu.be/outro12"]
    assert falhas == [("https://youtu.be/falha00", "vídeo privado")]
    assert itens == [(1, 3), (2, 3), (3, 3)]


def test_baixar_varios_para_ao_cancelar(tmp_path):
    chamadas = []
    d = criar(chamadas=chamadas)
    d.cancelar()
    with pytest.raises(DownloadCancelado) as cancelamento:
        d.baixar_varios([URL, URL], TIPO_VIDEO, str(tmp_path))
    assert chamadas == []
    assert cancelamento.value.baixados == []


def test_cancelamento_no_lote_informa_o_que_ja_foi_salvo(tmp_path):
    d = criar()
    urls = [URL, "https://youtu.be/segundo1"]

    def ao_iniciar_item(indice, _total, _url):
        if indice == 2:
            d.cancelar()  # usuário cancela logo depois do primeiro item terminar

    with pytest.raises(DownloadCancelado) as cancelamento:
        d.baixar_varios(urls, TIPO_AUDIO, str(tmp_path), ao_iniciar_item=ao_iniciar_item)
    assert [url for url, _ in cancelamento.value.baixados] == [URL]
    assert os.listdir(tmp_path) == ["Titulo.m4a"]


@pytest.mark.parametrize("tipo,nome", [(TIPO_AUDIO, "Titulo"), (TIPO_VIDEO, "v1080p")])
def test_nao_sobrescreve_arquivo_existente(tmp_path, tipo, nome):
    extensao = ".m4a" if tipo == TIPO_AUDIO else ".mp4"
    existente = tmp_path / f"{nome}{extensao}"
    existente.write_bytes(b"arquivo antigo do usuario")
    caminho = criar().baixar(URL, tipo, str(tmp_path))
    assert os.path.basename(caminho) == f"{nome} (2){extensao}"
    assert existente.read_bytes() == b"arquivo antigo do usuario"


@pytest.mark.parametrize("tipo", [TIPO_AUDIO, TIPO_VIDEO])
def test_falha_no_meio_nao_deixa_arquivo_pela_metade(tmp_path, tipo):
    with pytest.raises(ConnectionError):
        criar(erro_audio=ConnectionError("rede caiu")).baixar(URL, tipo, str(tmp_path))
    assert os.listdir(tmp_path) == []


def test_falha_do_ffmpeg_nao_deixa_arquivo_na_pasta(tmp_path):
    def juntar_com_erro(_imagem, _audio, saida):
        open(saida, "wb").close()  # ffmpeg começou a escrever e falhou
        raise RuntimeError("ffmpeg falhou")

    with pytest.raises(RuntimeError):
        criar(juntador=juntar_com_erro).baixar(URL, TIPO_VIDEO, str(tmp_path))
    assert os.listdir(tmp_path) == []


def test_limpar_sobras_temporarias_apaga_so_as_antigas_do_app(tmp_path):
    from analisador.downloader import limpar_sobras_temporarias

    for nome in ("analisador-video-velha", "analisador-video-nova", "outro-programa-velha"):
        (tmp_path / nome).mkdir()
        (tmp_path / nome / "parte.mp4").touch()
    agora = 10_000_000
    os.utime(tmp_path / "analisador-video-velha", (agora - 7 * 3600,) * 2)
    os.utime(tmp_path / "outro-programa-velha", (agora - 7 * 3600,) * 2)
    os.utime(tmp_path / "analisador-video-nova", (agora - 60,) * 2)

    assert limpar_sobras_temporarias(pasta=str(tmp_path), agora=agora) == 1
    assert sorted(os.listdir(tmp_path)) == ["analisador-video-nova", "outro-programa-velha"]
