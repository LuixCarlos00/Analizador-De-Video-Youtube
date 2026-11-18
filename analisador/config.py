"""Configurações centrais (pastas de saída e parâmetros da transcrição)."""

import os
import sys

PASTA_USUARIO = os.path.expanduser("~")

PASTA_VIDEOS = os.path.join(PASTA_USUARIO, "Videos_Downloads")
PASTA_AUDIOS = os.path.join(PASTA_USUARIO, "Audios_Downloads")
PASTA_TRANSCRICOES = os.path.join(PASTA_USUARIO, "Transcricoes")

IDIOMA_TRANSCRICAO = "pt-BR"

# A API gratuita do Google rejeita trechos longos; 10 s mantém a taxa de erro baixa.
TAMANHO_TRECHO_MS = 10 * 1000

EXTENSOES_AUDIO = ("*.mp3", "*.mp4", "*.m4a", "*.wav", "*.ogg", "*.webm")


def pasta_da_aplicacao():
    """Retorna a pasta onde o app está instalado.

    Returns:
        str: pasta do executável (quando empacotado pelo PyInstaller) ou a raiz do projeto.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def configurar_ffmpeg_local(pasta_app=None):
    """Coloca o ffmpeg que acompanha o app (``<app>/ffmpeg/bin``) no início do PATH.

    O instalador do Windows baixa o ffmpeg para dentro da pasta do app; assim o
    pydub o encontra sem o usuário precisar configurar nada no sistema.
    Precisa rodar antes do primeiro ``import pydub``.

    Args:
        pasta_app (str | None): pasta do app (injetável para testes).

    Returns:
        bool: True se encontrou e configurou o ffmpeg local.
    """
    pasta_bin = os.path.join(pasta_app or pasta_da_aplicacao(), "ffmpeg", "bin")
    if not os.path.isdir(pasta_bin):
        return False
    caminhos = os.environ.get("PATH", "").split(os.pathsep)
    if pasta_bin not in caminhos:
        os.environ["PATH"] = os.pathsep.join([pasta_bin] + caminhos)
    return True


def ocultar_janelas_de_console():
    """No .exe do Windows, impede que node/ffmpeg abram janelas pretas de terminal.

    O app é empacotado sem console (janela gráfica). Programas de console chamados
    por ele (o Node usado pela pytubefix e o ffmpeg usado pelo pydub) abririam uma
    janela preta a cada execução. Aqui o ``subprocess.Popen`` passa a usar
    CREATE_NO_WINDOW por padrão. Não faz nada fora do Windows ou fora do .exe.

    Returns:
        bool: True se o ajuste foi aplicado.
    """
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return False

    import subprocess

    if getattr(subprocess.Popen, "_sem_console", False):
        return True
    popen_original = subprocess.Popen

    class PopenSemConsole(popen_original):
        _sem_console = True

        def __init__(self, *args, **kwargs):
            kwargs["creationflags"] = kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)

    subprocess.Popen = PopenSemConsole
    return True
