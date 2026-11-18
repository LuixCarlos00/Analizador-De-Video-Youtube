"""Download de vídeos e áudios do YouTube com suporte a cancelamento real.

Sobre vídeo: o YouTube quase não oferece mais arquivos "progressivos" (vídeo e áudio
juntos; quando existem, só em 360p). Por isso o vídeo é baixado em duas partes, a
melhor imagem e o melhor áudio, e juntado com o ffmpeg sem recodificar
(rápido e sem perda de qualidade).
"""

import os
import shutil
import subprocess
import tempfile
import threading

from .utils import (
    calcular_percentual,
    caminho_sem_conflito,
    e_url_youtube_valida,
    garantir_pasta,
    mensagem_de_erro_amigavel,
)

TIPO_VIDEO = "video"
TIPO_AUDIO = "audio"

# 1080p em H.264 abre em qualquer player; 1440p/4K costumam vir em VP9/AV1, que o player
# padrão do Windows não abre sem extensões extras.
RESOLUCAO_MAXIMA = 1080

# Parte da barra de progresso de cada etapa do download de vídeo.
_FAIXA_IMAGEM = (0, 85)
_FAIXA_AUDIO = (85, 13)


class DownloadCancelado(Exception):
    """Lançada de dentro do callback de progresso para interromper o download em andamento.

    Attributes:
        baixados (list[tuple[str, str]]): em lotes, os (url, arquivo) salvos antes do cancelamento.
    """

    def __init__(self, baixados=None):
        super().__init__("Download cancelado pelo usuário.")
        self.baixados = list(baixados or [])


def pasta_temporaria(prefixo):
    """Pasta temporária que some sozinha ao final.

    ``ignore_cleanup_errors``: no Windows, antivírus/indexador podem segurar um arquivo por
    instantes; a limpeza falhar não pode transformar um download bem-sucedido em erro.

    Args:
        prefixo (str): prefixo do nome da pasta (facilita achar sobras).

    Returns:
        tempfile.TemporaryDirectory: use com ``with``.
    """
    return tempfile.TemporaryDirectory(prefix=prefixo, ignore_cleanup_errors=True)


PREFIXO_TEMPORARIO = "analisador-"


def limpar_sobras_temporarias(idade_minima_s=6 * 3600, pasta=None, agora=None):
    """Apaga pastas temporárias antigas deixadas quando o app foi fechado no meio de um download.

    Só apaga pastas com mais de ``idade_minima_s`` segundos, para não atrapalhar
    outra janela do app que esteja trabalhando agora.

    Args:
        idade_minima_s (int): idade mínima (pela data de modificação) para apagar.
        pasta (str | None): pasta temporária do sistema (injetável para testes).
        agora (float | None): instante atual em segundos (injetável para testes).

    Returns:
        int: quantidade de pastas apagadas.
    """
    import time

    pasta = pasta or tempfile.gettempdir()
    agora = agora if agora is not None else time.time()
    apagadas = 0
    try:
        entradas = list(os.scandir(pasta))
    except OSError:
        return 0
    for entrada in entradas:
        try:
            if (entrada.name.startswith(PREFIXO_TEMPORARIO) and entrada.is_dir(follow_symlinks=False)
                    and agora - entrada.stat(follow_symlinks=False).st_mtime > idade_minima_s):
                shutil.rmtree(entrada.path, ignore_errors=True)
                apagadas += 1
        except OSError:
            continue
    return apagadas


def mover_sem_sobrescrever(origem, pasta_destino, nome):
    """Move um arquivo completo para a pasta do usuário sem apagar outro de mesmo nome.

    Args:
        origem (str): arquivo pronto (na pasta temporária).
        pasta_destino (str): pasta final.
        nome (str): nome desejado; vira "nome (2).mp4" se já existir.

    Returns:
        str: caminho final.
    """
    destino = caminho_sem_conflito(garantir_pasta(pasta_destino), nome)
    shutil.move(origem, destino)
    return destino


def criar_youtube(url, on_progress_callback):
    """Cria o objeto YouTube da pytubefix (import tardio: testes não precisam da biblioteca).

    Args:
        url (str): link do vídeo.
        on_progress_callback (Callable | None): chamado a cada pedaço baixado.

    Returns:
        pytubefix.YouTube: objeto do vídeo.
    """
    from pytubefix import YouTube

    return YouTube(url, on_progress_callback=on_progress_callback)


def _altura(stream):
    """Converte a resolução "1080p" em 1080 (0 se desconhecida)."""
    try:
        return int(str(getattr(stream, "resolution", "") or "").rstrip("p") or 0)
    except ValueError:
        return 0


def escolher_stream_de_imagem(streams, resolucao_maxima=RESOLUCAO_MAXIMA):
    """Escolhe o melhor stream só de imagem em MP4, preferindo H.264 (máxima compatibilidade).

    Args:
        streams (Iterable): streams de vídeo sem áudio em MP4.
        resolucao_maxima (int): altura máxima aceita (ex.: 1080).

    Returns:
        Stream | None: o stream escolhido.
    """
    candidatos = [s for s in streams if 0 < _altura(s) <= resolucao_maxima]
    if not candidatos:
        return None

    def nota(stream):
        h264 = str(getattr(stream, "video_codec", "") or "").startswith("avc1")
        return (h264, _altura(stream), getattr(stream, "fps", 0) or 0)

    return max(candidatos, key=nota)


def juntar_com_ffmpeg(caminho_imagem, caminho_audio, caminho_saida):
    """Junta imagem e áudio num MP4 sem recodificar.

    Args:
        caminho_imagem (str): arquivo só com a imagem.
        caminho_audio (str): arquivo só com o áudio.
        caminho_saida (str): MP4 final.

    Raises:
        RuntimeError: o ffmpeg falhou.
    """
    comando = [shutil.which("ffmpeg") or "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
               "-i", caminho_imagem, "-i", caminho_audio,
               "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", "-movflags", "+faststart",
               caminho_saida]
    # encoding explícito: no Windows o padrão seria cp1252 e a saída do ffmpeg vem em UTF-8.
    resultado = subprocess.run(comando, capture_output=True, stdin=subprocess.DEVNULL,
                               encoding="utf-8", errors="replace")
    if resultado.returncode != 0:
        raise RuntimeError(f"O ffmpeg não conseguiu juntar imagem e áudio: {resultado.stderr.strip()[-300:]}")


class Downloader:
    """Baixa vídeos/áudios do YouTube, reportando progresso e permitindo cancelar.

    O cancelamento funciona lançando ``DownloadCancelado`` dentro do callback de
    progresso da pytubefix, o que interrompe o laço de escrita do arquivo. Todo download
    acontece numa pasta temporária e só é movido para a pasta do usuário quando completo,
    então cancelamentos e falhas nunca deixam arquivo pela metade nem sobrescrevem outro.
    """

    def __init__(self, youtube_factory=criar_youtube, juntar=juntar_com_ffmpeg,
                 ffmpeg_disponivel=lambda: shutil.which("ffmpeg") is not None):
        """
        Args:
            youtube_factory (Callable[[str, Callable], object]): cria o objeto YouTube.
            juntar (Callable[[str, str, str], None]): junta imagem + áudio.
            ffmpeg_disponivel (Callable[[], bool]): diz se dá para juntar com ffmpeg.
            Os três são injetáveis para testes.
        """
        self._youtube_factory = youtube_factory
        self._juntar = juntar
        self._ffmpeg_disponivel = ffmpeg_disponivel
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

        # Faixa da barra (início, tamanho) da etapa atual: o vídeo tem duas etapas de download.
        faixa = {"inicio": 0, "tamanho": 100}

        def _callback(stream, _chunk, bytes_restantes):
            if self._cancelar.is_set():
                raise DownloadCancelado()
            if ao_progredir:
                total = getattr(stream, "filesize", 0)
                parcial = calcular_percentual(total - bytes_restantes, total)
                ao_progredir(faixa["inicio"] + parcial * faixa["tamanho"] / 100)

        yt = self._youtube_factory(url, _callback)

        if tipo == TIPO_AUDIO:
            return self._baixar_para(yt.streams.get_audio_only(), pasta_destino)

        imagem = None
        if self._ffmpeg_disponivel():
            imagem = escolher_stream_de_imagem(yt.streams.filter(only_video=True, file_extension="mp4"))
        if imagem is None:
            # Sem ffmpeg (ou bloqueado pelo Windows) não dá para juntar: tenta o formato
            # progressivo, que nem sempre existe e vai no máximo até 360p/720p.
            progressivo = yt.streams.get_highest_resolution()
            if progressivo is None and not self._ffmpeg_disponivel():
                raise RuntimeError("Para baixar vídeo é preciso o ffmpeg. Rode o instalador de novo.")
            return self._baixar_para(progressivo, pasta_destino)

        audio = yt.streams.get_audio_only()
        if audio is None:
            raise RuntimeError("Nenhum áudio disponível para este vídeo.")

        with pasta_temporaria("analisador-video-") as pasta_temp:
            nome_final = os.path.basename(imagem.get_file_path(output_path=pasta_temp))
            faixa["inicio"], faixa["tamanho"] = _FAIXA_IMAGEM
            arquivo_imagem = self._baixar_stream(imagem, pasta_temp, filename="imagem.mp4")
            faixa["inicio"], faixa["tamanho"] = _FAIXA_AUDIO
            arquivo_audio = self._baixar_stream(audio, pasta_temp, filename="audio.m4a")
            if self.cancelado:
                raise DownloadCancelado()
            saida_temp = os.path.join(pasta_temp, "final.mp4")
            self._juntar(arquivo_imagem, arquivo_audio, saida_temp)
            caminho_final = mover_sem_sobrescrever(saida_temp, pasta_destino, nome_final)
        if ao_progredir:
            ao_progredir(100)
        return caminho_final

    def _baixar_para(self, stream, pasta_destino):
        """Baixa um stream único numa pasta temporária e só move para o destino quando completo."""
        with pasta_temporaria("analisador-download-") as pasta_temp:
            arquivo = self._baixar_stream(stream, pasta_temp)
            return mover_sem_sobrescrever(arquivo, pasta_destino, os.path.basename(arquivo))

    @staticmethod
    def _baixar_stream(stream, pasta, filename=None):
        """Baixa o stream na pasta indicada (sempre temporária: arquivo parcial nunca chega ao usuário)."""
        if stream is None:
            raise RuntimeError("Nenhum formato disponível para download deste vídeo.")
        return stream.download(output_path=pasta, filename=filename, skip_existing=False)

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
            tuple[list[tuple[str, str]], list[tuple[str, str]]]:
                ([(url, arquivo salvo)], [(url, mensagem de erro)]).

        Raises:
            DownloadCancelado: o usuário cancelou; os itens restantes não são baixados.
                O atributo ``baixados`` traz o que já tinha sido salvo antes do cancelamento.
        """
        baixados, falhas = [], []
        for indice, url in enumerate(urls, start=1):
            if self.cancelado:
                # Leva junto o que já foi salvo: o cancelamento pode chegar logo após um item terminar.
                raise DownloadCancelado(baixados)
            if ao_iniciar_item:
                ao_iniciar_item(indice, len(urls), url)
            try:
                baixados.append((url, self.baixar(url, tipo, pasta_destino, ao_progredir)))
            except DownloadCancelado as erro:
                raise DownloadCancelado(baixados) from erro
            except Exception as erro:  # noqa: BLE001 - um link ruim não deve parar o lote
                falhas.append((url, mensagem_de_erro_amigavel(erro)))
        return baixados, falhas
