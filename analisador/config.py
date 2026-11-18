"""Configurações centrais (pastas de saída e parâmetros da transcrição)."""

import os
import re
import sys

PASTA_USUARIO = os.path.expanduser("~")

# GUID da pasta "Downloads" no Windows (FOLDERID_Downloads).
_FOLDERID_DOWNLOADS = "{374DE290-123F-4565-9164-39C4925E467B}"


def _pasta_downloads_windows():
    """Pergunta ao Windows onde fica a pasta Downloads (ela pode ter sido movida, ex.: OneDrive)."""
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

    guid = GUID()
    ctypes.oledll.ole32.CLSIDFromString(_FOLDERID_DOWNLOADS, ctypes.byref(guid))
    caminho = ctypes.c_wchar_p()
    ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(caminho))
    try:
        return caminho.value
    finally:
        ctypes.windll.ole32.CoTaskMemFree(caminho)


def _pasta_downloads_xdg(home):
    """Lê a pasta Downloads configurada no Linux (~/.config/user-dirs.dirs), que pode ter outro nome."""
    arquivo = os.path.join(home, ".config", "user-dirs.dirs")
    try:
        with open(arquivo, encoding="utf-8") as f:
            for linha in f:
                achado = re.match(r'\s*XDG_DOWNLOAD_DIR\s*=\s*"(.+)"', linha)
                if achado:
                    pasta = os.path.normpath(achado.group(1).replace("$HOME", home))
                    # "$HOME/" significa que o usuário desativou a pasta Downloads: usa o padrão.
                    return None if pasta == os.path.normpath(home) else pasta
    except OSError:
        pass
    return None


def pasta_downloads(home=None):
    """Retorna a pasta Downloads do usuário no sistema operacional atual.

    Args:
        home (str | None): pasta do usuário (injetável para testes).

    Returns:
        str: caminho da pasta Downloads; cai em ``~/Downloads`` se não conseguir descobrir.
    """
    home = home or PASTA_USUARIO
    descoberta = None
    try:
        if os.name == "nt":
            descoberta = _pasta_downloads_windows()
        elif sys.platform != "darwin":
            descoberta = _pasta_downloads_xdg(home)
    except Exception:  # noqa: BLE001 - na dúvida, usa o caminho padrão
        descoberta = None
    return descoberta or os.path.join(home, "Downloads")


# Tudo fica organizado numa pasta própria dentro de Downloads.
PASTA_BASE = os.path.join(pasta_downloads(), "Analisador YouTube")
PASTA_VIDEOS = os.path.join(PASTA_BASE, "Videos")
PASTA_AUDIOS = os.path.join(PASTA_BASE, "Audios")
PASTA_TRANSCRICOES = os.path.join(PASTA_BASE, "Transcricoes")

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
    CREATE_NO_WINDOW por padrão. Só age no Windows, quando o app roda sem console
    (pelo .exe ou pelo ``pythonw.exe``, que é como o atalho do instalador abre o app).

    Returns:
        bool: True se o ajuste foi aplicado.
    """
    sem_console = getattr(sys, "frozen", False) or os.path.basename(sys.executable).lower() == "pythonw.exe"
    if os.name != "nt" or not sem_console:
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
