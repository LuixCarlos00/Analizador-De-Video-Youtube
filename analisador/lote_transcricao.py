"""Transcrição de vários itens de uma vez (links do YouTube e arquivos de áudio misturados)."""

import os
import threading
from dataclasses import dataclass

from .config import IDIOMA_TRANSCRICAO
from .transcricao_youtube import ORIGEM_AUDIO, ResultadoTranscricao, TranscritorYoutube
from .transcriber import TranscricaoCancelada, Transcritor
from .utils import (
    caminho_sem_conflito,
    garantir_pasta,
    mensagem_de_erro_amigavel,
    nome_arquivo_transcricao,
    nome_base_do_arquivo,
)

TIPO_LINK = "link"
TIPO_ARQUIVO = "arquivo"


@dataclass(frozen=True)
class ItemTranscricao:
    """Um item da fila de transcrição.

    Attributes:
        tipo (str): ``TIPO_LINK`` ou ``TIPO_ARQUIVO``.
        valor (str): o link do YouTube ou o caminho do arquivo de áudio.
    """

    tipo: str
    valor: str

    @property
    def rotulo(self):
        """str: texto curto para mostrar na lista da interface."""
        if self.tipo == TIPO_ARQUIVO:
            return f"[arquivo]  {os.path.basename(self.valor)}"
        return f"[YouTube]  {self.valor}"


@dataclass
class ItemTranscrito:
    """Resultado de um item transcrito com sucesso.

    Attributes:
        item (ItemTranscricao): item de origem.
        resultado (ResultadoTranscricao): texto e de onde veio.
        arquivo_txt (str): onde o texto foi salvo.
    """

    item: ItemTranscricao
    resultado: ResultadoTranscricao
    arquivo_txt: str


class TranscritorEmLote:
    """Transcreve uma lista de itens em sequência, salvando cada texto num .txt.

    Um item com problema não interrompe os outros; o cancelamento interrompe tudo.
    """

    def __init__(self, pasta_saida, idioma=IDIOMA_TRANSCRICAO,
                 criar_transcritor_youtube=TranscritorYoutube, criar_transcritor_arquivo=Transcritor):
        """
        Args:
            pasta_saida (str): pasta onde os .txt serão salvos.
            idioma (str): idioma da transcrição.
            criar_transcritor_youtube (Callable[..., TranscritorYoutube]): injetável para testes.
            criar_transcritor_arquivo (Callable[..., Transcritor]): injetável para testes.
        """
        self.pasta_saida = pasta_saida
        self.idioma = idioma
        self._criar_youtube = criar_transcritor_youtube
        self._criar_arquivo = criar_transcritor_arquivo
        self._cancelar = threading.Event()
        self._atual = None
        self._trava = threading.Lock()  # protege _atual: cancelar() vem de outra thread

    def cancelar(self):
        """Cancela o item atual e os próximos."""
        self._cancelar.set()
        with self._trava:
            if self._atual is not None:
                self._atual.cancelar()

    def transcrever(self, itens, usar_legendas=True, ao_progredir=None, ao_status=None, ao_iniciar_item=None):
        """Transcreve todos os itens.

        Args:
            itens (list[ItemTranscricao]): fila de itens.
            usar_legendas (bool): para links, usar a legenda do YouTube quando existir.
            ao_progredir (Callable[[float], None] | None): progresso do item atual (0-100).
            ao_status (Callable[[str], None] | None): etapa atual do item, em texto.
            ao_iniciar_item (Callable[[int, int, ItemTranscricao], None] | None): (índice, total, item).

        Returns:
            tuple[list[ItemTranscrito], list[tuple[ItemTranscricao, str]]]: (sucessos, falhas com mensagem).

        Raises:
            TranscricaoCancelada: o usuário cancelou.
        """
        sucessos, falhas = [], []
        for indice, item in enumerate(itens, start=1):
            if self._cancelar.is_set():
                raise TranscricaoCancelada()
            if ao_iniciar_item:
                ao_iniciar_item(indice, len(itens), item)
            try:
                resultado = self._transcrever_item(item, usar_legendas, ao_progredir, ao_status)
                if not resultado.texto.strip():
                    falhas.append((item, "Nenhuma fala foi reconhecida."))
                    continue
                sucessos.append(ItemTranscrito(item, resultado, self._salvar(resultado)))
            except TranscricaoCancelada:
                raise
            except Exception as erro:  # noqa: BLE001 - um item ruim não deve parar o lote
                if self._cancelar.is_set():
                    raise TranscricaoCancelada() from erro
                falhas.append((item, mensagem_de_erro_amigavel(erro)))
        return sucessos, falhas

    def _transcrever_item(self, item, usar_legendas, ao_progredir, ao_status):
        if item.tipo == TIPO_LINK:
            transcritor = self._criar_youtube(idioma=self.idioma)
            self._definir_atual(transcritor)
            return transcritor.transcrever(item.valor, ao_progredir, ao_status, usar_legendas)

        transcritor = self._criar_arquivo(idioma=self.idioma)
        self._definir_atual(transcritor)
        if ao_status:
            ao_status("Transcrevendo o áudio (pode demorar): ")
        texto, nao_entendidos = transcritor.transcrever(item.valor, ao_progredir)
        return ResultadoTranscricao(titulo=nome_base_do_arquivo(item.valor), texto=texto,
                                    origem=ORIGEM_AUDIO, detalhe="arquivo de áudio",
                                    nao_entendidos=nao_entendidos)

    def _definir_atual(self, transcritor):
        with self._trava:
            self._atual = transcritor
            if self._cancelar.is_set():  # cancelado entre um item e outro
                transcritor.cancelar()

    def _salvar(self, resultado):
        garantir_pasta(self.pasta_saida)
        destino = caminho_sem_conflito(self.pasta_saida, nome_arquivo_transcricao(resultado.titulo))
        with open(destino, "w", encoding="utf-8") as arquivo:
            arquivo.write(resultado.texto)
        return destino
