"""Transcrição direto de um link do YouTube, sem o usuário precisar baixar o áudio antes.

Estratégia, da mais rápida para a mais lenta:
1. Legenda do próprio YouTube no idioma pedido (instantâneo, cobre o vídeo inteiro,
   não precisa de ffmpeg nem do serviço do Google). Prefere a legenda feita pelo autor
   e, se não houver, usa a gerada automaticamente pelo YouTube.
2. Se não houver legenda: baixa só o áudio numa pasta temporária, transcreve com o
   ``Transcritor`` e apaga o áudio no final.
"""

import threading
from dataclasses import dataclass

from .config import IDIOMA_TRANSCRICAO
from .downloader import TIPO_AUDIO, DownloadCancelado, Downloader, criar_youtube, pasta_temporaria
from .transcriber import TranscricaoCancelada, Transcritor
from .utils import e_url_youtube_valida

ORIGEM_LEGENDA = "legenda"
ORIGEM_AUDIO = "audio"

# Parte da barra de progresso reservada ao download do áudio; o resto é da transcrição.
_PESO_DOWNLOAD = 30


@dataclass
class ResultadoTranscricao:
    """Resultado da transcrição de um vídeo.

    Attributes:
        titulo (str): título do vídeo (usado no nome do arquivo salvo).
        texto (str): texto transcrito.
        origem (str): ``ORIGEM_LEGENDA`` ou ``ORIGEM_AUDIO``.
        detalhe (str): ex.: nome da legenda usada ("Português (gerado automaticamente)").
        nao_entendidos (int): trechos de áudio não reconhecidos (só quando origem é áudio).
    """

    titulo: str
    texto: str
    origem: str
    detalhe: str = ""
    nao_entendidos: int = 0


def escolher_legenda(legendas, idioma):
    """Escolhe a melhor legenda disponível para o idioma.

    Ordem de preferência: feita pelo autor com o idioma exato (ex.: ``pt-BR``),
    feita pelo autor com o mesmo idioma base (``pt``), e por último a automática (``a.pt``).

    Args:
        legendas (Iterable): legendas da pytubefix (cada uma com ``.code``, ex.: "pt", "a.pt").
        idioma (str): idioma desejado (ex.: "pt-BR").

    Returns:
        Caption | None: a legenda escolhida, ou None se não houver nenhuma no idioma.
    """
    idioma = idioma.lower()
    lingua = idioma.split("-")[0]
    melhor, melhor_nota = None, 0
    for legenda in legendas:
        codigo = (getattr(legenda, "code", "") or "").lower()
        automatica = codigo.startswith("a.")
        codigo = codigo[2:] if automatica else codigo
        if codigo.split("-")[0] != lingua:
            continue
        nota = 1 if automatica else (3 if codigo == idioma else 2)
        if nota > melhor_nota:
            melhor, melhor_nota = legenda, nota
    return melhor


class TranscritorYoutube:
    """Transcreve um vídeo do YouTube a partir do link (legenda ou áudio)."""

    def __init__(self, idioma=IDIOMA_TRANSCRICAO, youtube_factory=criar_youtube,
                 downloader=None, transcritor=None):
        """
        Args:
            idioma (str): idioma da transcrição (ex.: "pt-BR").
            youtube_factory (Callable[[str, Callable | None], object]): cria o objeto YouTube.
            downloader (Downloader | None): injetável para testes.
            transcritor (Transcritor | None): injetável para testes.
        """
        self.idioma = idioma
        self._youtube_factory = youtube_factory
        self._downloader = downloader or Downloader(youtube_factory)
        self._transcritor = transcritor or Transcritor(idioma=idioma)
        self._cancelar = threading.Event()

    def cancelar(self):
        """Cancela a etapa atual (busca, download ou transcrição)."""
        self._cancelar.set()
        self._downloader.cancelar()
        self._transcritor.cancelar()

    def _verificar_cancelamento(self):
        if self._cancelar.is_set():
            raise TranscricaoCancelada()

    def transcrever(self, url, ao_progredir=None, ao_status=None, usar_legendas=True):
        """Transcreve o vídeo do link.

        Args:
            url (str): link do vídeo no YouTube.
            ao_progredir (Callable[[float], None] | None): recebe o percentual (0-100).
            ao_status (Callable[[str], None] | None): recebe a etapa atual, em texto.
            usar_legendas (bool): se False, ignora as legendas e sempre transcreve o áudio.

        Returns:
            ResultadoTranscricao: texto e de onde ele veio.

        Raises:
            ValueError: URL inválida.
            TranscricaoCancelada: o usuário cancelou.
            ErroServicoTranscricao: falha no serviço de reconhecimento de fala.
        """
        if not e_url_youtube_valida(url):
            raise ValueError(f"URL inválida: {url}")
        progredir = ao_progredir or (lambda _p: None)
        status = ao_status or (lambda _s: None)

        status("Buscando informações do vídeo... ")
        yt = self._youtube_factory(url, None)
        titulo = yt.title
        self._verificar_cancelamento()

        if usar_legendas:
            resultado = self._tentar_legenda(yt, titulo, status)
            if resultado:
                progredir(100)
                return resultado
            self._verificar_cancelamento()

        with pasta_temporaria("analisador-transcricao-") as pasta_temp:
            status("Baixando o áudio do vídeo: ")
            try:
                caminho_audio = self._downloader.baixar(
                    url, TIPO_AUDIO, pasta_temp, lambda p: progredir(p * _PESO_DOWNLOAD / 100))
            except DownloadCancelado as erro:
                raise TranscricaoCancelada() from erro
            self._verificar_cancelamento()

            status("Transcrevendo o áudio (pode demorar): ")
            texto, nao_entendidos = self._transcritor.transcrever(
                caminho_audio,
                lambda p: progredir(_PESO_DOWNLOAD + p * (100 - _PESO_DOWNLOAD) / 100))

        return ResultadoTranscricao(titulo=titulo, texto=texto, origem=ORIGEM_AUDIO,
                                    detalhe="reconhecimento de voz do áudio",
                                    nao_entendidos=nao_entendidos)

    def _tentar_legenda(self, yt, titulo, status):
        """Retorna o resultado a partir da legenda, ou None se não houver legenda utilizável."""
        try:
            legenda = escolher_legenda(yt.captions, self.idioma)
            if legenda is None:
                status("Vídeo sem legenda em português; usando o áudio. ")
                return None
            nome = getattr(legenda, "name", legenda.code)
            status(f"Lendo a legenda do YouTube ({nome})... ")
            texto = (legenda.generate_txt_captions() or "").strip()
        except Exception:  # noqa: BLE001 - qualquer falha na legenda: cai para o áudio
            return None
        if not texto:
            return None
        return ResultadoTranscricao(titulo=titulo, texto=texto, origem=ORIGEM_LEGENDA,
                                    detalhe=f"legenda do YouTube: {nome}")
