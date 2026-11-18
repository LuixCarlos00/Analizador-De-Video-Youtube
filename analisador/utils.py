"""Funções utilitárias sem dependência de interface gráfica (fáceis de testar)."""

import os
import re
import subprocess
import sys
from datetime import datetime

# Aceita youtube.com/watch, youtube.com/shorts, m.youtube.com, music.youtube.com e youtu.be.
_REGEX_URL_YOUTUBE = re.compile(
    r"^(https?://)?((www|m|music)\.)?(youtube\.com/(watch\?.*v=|shorts/|live/|embed/)|youtu\.be/)[\w-]{6,}",
    re.IGNORECASE,
)

# Separadores aceitos na lista de URLs: vírgula, ponto e vírgula, quebra de linha e espaços.
_REGEX_SEPARADORES = re.compile(r"[,;\s]+")


def e_url_youtube_valida(url):
    """Verifica se o texto é um link de vídeo do YouTube.

    Args:
        url (str): texto informado pelo usuário.

    Returns:
        bool: True se parecer um link de vídeo do YouTube.
    """
    if not url:
        return False
    return _REGEX_URL_YOUTUBE.match(url.strip()) is not None


def extrair_urls(texto):
    """Quebra o texto em uma lista de URLs, ignorando vazios e duplicados (mantendo a ordem).

    Args:
        texto (str): links separados por vírgula, ponto e vírgula, espaço ou quebra de linha.

    Returns:
        list[str]: URLs na ordem em que apareceram.
    """
    vistos = set()
    urls = []
    for parte in _REGEX_SEPARADORES.split(texto or ""):
        if parte and parte not in vistos:
            vistos.add(parte)
            urls.append(parte)
    return urls


def calcular_percentual(processado, total):
    """Calcula o percentual de progresso limitado entre 0 e 100.

    Args:
        processado (int | float): quantidade já processada.
        total (int | float): quantidade total.

    Returns:
        float: percentual entre 0.0 e 100.0 (0.0 se o total for inválido).
    """
    if not total or total <= 0:
        return 0.0
    return max(0.0, min(100.0, processado / total * 100))


def garantir_pasta(caminho):
    """Cria a pasta (e as pastas-pai) caso ainda não exista.

    Args:
        caminho (str): caminho da pasta.

    Returns:
        str: o próprio caminho, para encadear chamadas.
    """
    os.makedirs(caminho, exist_ok=True)
    return caminho


def nome_arquivo_transcricao(arquivo_origem, agora=None):
    """Gera um nome legível para o arquivo de transcrição.

    Usa o nome do áudio de origem + data/hora, em vez de uma string aleatória,
    para o usuário saber de qual áudio veio cada transcrição.

    Args:
        arquivo_origem (str): caminho do arquivo de áudio transcrito.
        agora (datetime | None): data/hora usada no nome (injetável para testes).

    Returns:
        str: nome do arquivo, ex.: "aula-01_2026-11-18_14-30-00.txt".
    """
    agora = agora or datetime.now()
    base = os.path.splitext(os.path.basename(arquivo_origem))[0] or "transcricao"
    base = re.sub(r'[\\/:*?"<>|]+', "_", base).strip() or "transcricao"
    return f"{base}_{agora:%Y-%m-%d_%H-%M-%S}.txt"


def abrir_pasta(caminho):
    """Abre a pasta no gerenciador de arquivos do sistema operacional.

    Args:
        caminho (str): pasta a ser aberta.
    """
    if os.name == "nt":
        os.startfile(caminho)  # type: ignore[attr-defined]  # só existe no Windows
    elif sys.platform == "darwin":
        subprocess.Popen(["open", caminho])
    else:
        subprocess.Popen(["xdg-open", caminho])
