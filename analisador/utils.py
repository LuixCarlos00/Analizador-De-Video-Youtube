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


# Títulos do YouTube podem ser enormes; o Windows limita o caminho completo a ~260 caracteres.
_TAMANHO_MAXIMO_NOME = 80


def nome_arquivo_transcricao(nome_base, agora=None):
    """Gera um nome legível e seguro para o arquivo de transcrição.

    Usa o nome de origem (arquivo de áudio ou título do vídeo) + data/hora, para o
    usuário saber de onde veio cada transcrição sem um arquivo sobrescrever o outro.

    Args:
        nome_base (str): nome do áudio (sem extensão) ou título do vídeo.
        agora (datetime | None): data/hora usada no nome (injetável para testes).

    Returns:
        str: nome do arquivo, ex.: "aula-01_2026-11-18_14-30-00.txt".
    """
    agora = agora or datetime.now()
    base = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", nome_base or "")
    base = base.strip(" .")[:_TAMANHO_MAXIMO_NOME].strip(" .") or "transcricao"
    return f"{base}_{agora:%Y-%m-%d_%H-%M-%S}.txt"


def caminho_sem_conflito(pasta, nome_arquivo):
    """Retorna um caminho que ainda não existe, acrescentando " (2)", " (3)"... se preciso.

    Evita que duas transcrições com o mesmo nome no mesmo segundo se sobrescrevam.

    Args:
        pasta (str): pasta de destino.
        nome_arquivo (str): nome desejado, com extensão.

    Returns:
        str: caminho livre.
    """
    base, extensao = os.path.splitext(nome_arquivo)
    caminho, contador = os.path.join(pasta, nome_arquivo), 2
    while os.path.exists(caminho):
        caminho = os.path.join(pasta, f"{base} ({contador}){extensao}")
        contador += 1
    return caminho


def nome_base_do_arquivo(caminho):
    """Retorna o nome do arquivo sem pasta e sem extensão (ex.: "/x/aula 01.mp3" -> "aula 01").

    Args:
        caminho (str): caminho do arquivo.

    Returns:
        str: nome sem extensão.
    """
    return os.path.splitext(os.path.basename(caminho))[0]


_ERRO_WINDOWS_BLOQUEIO_POLITICA = 4551  # "Uma política de controle de aplicativo bloqueou este arquivo"

# Erros da pytubefix (comparados pelo nome da classe, para não depender da biblioteca aqui).
# A ordem importa: classes mais específicas primeiro (várias herdam de VideoUnavailable).
_ERROS_YOUTUBE = (
    ("VideoPrivate", "Este vídeo é privado."),
    ("MembersOnly", "Este vídeo é exclusivo para membros do canal."),
    ("AgeRestricted", "Este vídeo tem restrição de idade e exige login."),
    ("AgeCheckRequired", "Este vídeo tem restrição de idade e exige login."),
    ("LoginRequired", "Este vídeo exige login no YouTube."),
    ("VideoRegionBlocked", "Este vídeo não está disponível no seu país."),
    ("VideoBlockedByCopyright", "Este vídeo foi bloqueado por direitos autorais."),
    ("VideoRemoved", "Este vídeo foi removido."),
    ("AccountTerminated", "A conta que publicou este vídeo foi encerrada."),
    ("LiveStream", "Transmissões ao vivo não podem ser baixadas enquanto estão no ar."),
    ("BotDetection", "O YouTube bloqueou temporariamente o acesso (detecção de robô). "
                     "Espere alguns minutos e tente de novo."),
    ("PoTokenRequired", "O YouTube bloqueou temporariamente o acesso. Espere alguns minutos e tente de novo."),
    ("VideoUnavailable", "Este vídeo não existe ou não está disponível. Confira o link."),
    ("RegexMatchError", "Não foi possível ler este link. Confira se ele está completo."),
)


def mensagem_de_erro_amigavel(erro):
    """Traduz erros técnicos conhecidos em uma mensagem que um usuário leigo entende.

    Args:
        erro (BaseException): exceção capturada.

    Returns:
        str: mensagem para exibir ao usuário.
    """
    texto = str(erro)
    nomes_das_classes = [classe.__name__ for classe in type(erro).__mro__]
    for trecho_do_nome, mensagem in _ERROS_YOUTUBE:
        if any(trecho_do_nome in nome for nome in nomes_das_classes):
            return mensagem
    if getattr(erro, "winerror", None) == _ERRO_WINDOWS_BLOQUEIO_POLITICA or re.search(r"\bWinError 4551\b", texto):
        return ("O Windows bloqueou um programa auxiliar (ffmpeg ou node) por uma política de segurança "
                "(Controle Inteligente de Aplicativos ou regra da empresa). "
                "Veja a seção \"Problemas comuns no Windows\" do README.\n\n"
                f"Detalhe técnico: {texto}")
    if isinstance(erro, FileNotFoundError) and ("ffmpeg" in texto.lower() or "ffprobe" in texto.lower()):
        return f"O ffmpeg não foi encontrado. Rode o instalador de novo.\n\nDetalhe técnico: {texto}"
    return texto


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
