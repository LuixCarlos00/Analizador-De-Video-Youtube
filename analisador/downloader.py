"""Download de vídeos e áudios do YouTube com suporte a cancelamento real."""

import os
import threading

from .utils import calcular_percentual, e_url_youtube_valida, garantir_pasta

TIPO_VIDEO = "video"
TIPO_AUDIO = "audio"


class DownloadCancelado(Exception):
    """Lançada de dentro do callback de progresso para interromper o download em andamento."""


def _youtube_padrao(url, on_progress_callback):
    # Import tardio: permite testar o módulo sem a pytubefix instalada.
    from pytubefix import YouTube

    return YouTube(url, on_progress_callback=on_progress_callback)


class Downloader:
    """Baixa vídeos/áudios do YouTube, reportando progresso e permitindo cancelar.

    O cancelamento funciona lançando ``DownloadCancelado`` dentro do callback de
    progresso da pytubefix, o que interrompe o laço de escrita do arquivo; o arquivo
    parcial é removido em seguida.
    """

    def __init__(self, youtube_factory=_youtube_padrao):
        """
        Args:
            youtube_factory (Callable[[str, Callable], object]): cria o objeto YouTube;
                injetável para testes.
        """
        self._youtube_factory = youtube_factory
        self._cancelar = threading.Event()

    def cancelar(self):
        """Sinaliza o cancelamento do download atual (e dos próximos de um lote)."""
        self._cancelar.set()

    @property
    def cancelado(self):
        """bool: True se o cancelamento foi solicitado."""
        return self._cancelar.is_set()

    def baixar(self, url, tipo, pasta_destino, ao_progredir=None):
        """Baixa um único vídeo ou áudio.

        Args:
            url (str): link do vídeo no YouTube.
            tipo (str): ``TIPO_VIDEO`` ou ``TIPO_AUDIO``.
            pasta_destino (str): pasta onde o arquivo será salvo.
            ao_progredir (Callable[[float], None] | None): recebe o percentual (0-100).

        Returns:
            str: caminho completo do arquivo baixado.

        Raises:
            ValueError: URL inválida ou tipo desconhecido.
            DownloadCancelado: o usuário cancelou o download.
            RuntimeError: nenhum stream disponível para o vídeo.
        """
        if not e_url_youtube_valida(url):
            raise ValueError(f"URL inválida: {url}")
        if tipo not in (TIPO_VIDEO, TIPO_AUDIO):
            raise ValueError(f"Tipo de download desconhecido: {tipo}")
        if self.cancelado:
            raise DownloadCancelado()

        garantir_pasta(pasta_destino)

        def _callback(stream, _chunk, bytes_restantes):
            if self._cancelar.is_set():
                raise DownloadCancelado()
            if ao_progredir:
                total = getattr(stream, "filesize", 0)
                ao_progredir(calcular_percentual(total - bytes_restantes, total))

        yt = self._youtube_factory(url, _callback)
        if tipo == TIPO_VIDEO:
            # get_highest_resolution retorna o maior stream "progressivo" (vídeo + áudio juntos).
            stream = yt.streams.get_highest_resolution()
        else:
            stream = yt.streams.get_audio_only()

        if stream is None:
            raise RuntimeError("Nenhum formato disponível para download deste vídeo.")

        try:
            return stream.download(output_path=pasta_destino)
        except DownloadCancelado:
            self._remover_parcial(stream, pasta_destino)
            raise

    def baixar_varios(self, urls, tipo, pasta_destino, ao_progredir=None, ao_iniciar_item=None):
        """Baixa vários links em sequência, continuando mesmo se algum falhar.

        Baixar em sequência (e não em paralelo) evita que vários downloads disputem
        a mesma barra de progresso e reduz o risco de bloqueio pelo YouTube.

        Args:
            urls (list[str]): links a baixar.
            tipo (str): ``TIPO_VIDEO`` ou ``TIPO_AUDIO``.
            pasta_destino (str): pasta onde os arquivos serão salvos.
            ao_progredir (Callable[[float], None] | None): progresso do item atual (0-100).
            ao_iniciar_item (Callable[[int, int, str], None] | None): recebe (indice, total, url).

        Returns:
            tuple[list[str], list[tuple[str, str]]]: (arquivos baixados, [(url, mensagem de erro)]).

        Raises:
            DownloadCancelado: o usuário cancelou; os itens restantes não são baixados.
        """
        baixados, falhas = [], []
        for indice, url in enumerate(urls, start=1):
            if self.cancelado:
                raise DownloadCancelado()
            if ao_iniciar_item:
                ao_iniciar_item(indice, len(urls), url)
            try:
                baixados.append(self.baixar(url, tipo, pasta_destino, ao_progredir))
            except DownloadCancelado:
                raise
            except Exception as erro:  # noqa: BLE001 - um link ruim não deve parar o lote
                falhas.append((url, str(erro)))
        return baixados, falhas

    @staticmethod
    def _remover_parcial(stream, pasta_destino):
        """Remove o arquivo incompleto deixado por um download cancelado (melhor esforço)."""
        try:
            caminho = stream.get_file_path(output_path=pasta_destino)
        except Exception:  # noqa: BLE001 - versões da lib variam; não é crítico
            return
        if caminho and os.path.isfile(caminho):
            try:
                os.remove(caminho)
            except OSError:
                pass
