"""Interface gráfica (Tkinter).

Regra de ouro do Tkinter: widgets só podem ser alterados pela thread principal.
Por isso as threads de trabalho nunca tocam na interface: elas colocam funções
numa fila (``_fila_ui``) que a thread principal esvazia a cada 100 ms.
"""

import os
import queue
import threading
import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk

from . import config
from .downloader import TIPO_AUDIO, TIPO_VIDEO, DownloadCancelado, Downloader
from .transcriber import ErroServicoTranscricao, TranscricaoCancelada, Transcritor
from .utils import (
    abrir_pasta,
    e_url_youtube_valida,
    extrair_urls,
    garantir_pasta,
    nome_arquivo_transcricao,
)

TEMAS = {
    "azul": {"fundo": "MidnightBlue", "texto": "white", "botao": "#007BFF"},
    "escuro": {"fundo": "#1a1a1a", "texto": "white", "botao": "#007BFF"},
}

INTERVALO_FILA_MS = 100


class Aplicacao:
    """Janela principal: download de vídeo/áudio (único ou em lote) e transcrição."""

    def __init__(self, root):
        """
        Args:
            root (tk.Tk): janela raiz do Tkinter.
        """
        self.root = root
        self._fila_ui = queue.Queue()
        self._tarefa_atual = None  # Downloader ou Transcritor em execução (para cancelar)
        self._thread_atual = None
        self._tema = "azul"
        self._botoes_acao = []

        root.geometry("1000x620")
        root.title("Downloader de Vídeos e Áudios do YouTube")
        root.protocol("WM_DELETE_WINDOW", self._ao_fechar)

        self._montar_layout()
        self._aplicar_tema()
        self.root.after(INTERVALO_FILA_MS, self._processar_fila_ui)

    # ------------------------------------------------------------------ layout

    def _montar_layout(self):
        frame_unico = tk.Frame(self.root)
        frame_unico.pack(pady=10)

        tk.Label(frame_unico, text="Baixar Vídeo").grid(row=0, column=0, sticky="w", padx=5, pady=(5, 0))
        self.entry_video = tk.Entry(frame_unico, width=75)
        self.entry_video.grid(row=1, column=0, padx=5, pady=5)
        self._botao(frame_unico, "Baixar Vídeo", lambda: self._baixar_unico(self.entry_video, TIPO_VIDEO)) \
            .grid(row=2, column=0, sticky="w", padx=5, pady=5)

        tk.Label(frame_unico, text="Baixar Áudio").grid(row=0, column=1, sticky="w", padx=5, pady=(5, 0))
        self.entry_audio = tk.Entry(frame_unico, width=75)
        self.entry_audio.grid(row=1, column=1, padx=5, pady=5)
        self._botao(frame_unico, "Baixar Áudio", lambda: self._baixar_unico(self.entry_audio, TIPO_AUDIO)) \
            .grid(row=2, column=1, sticky="w", padx=5, pady=5)

        frame_lote = tk.Frame(self.root)
        frame_lote.pack(pady=10)

        texto_ajuda = "(um link por linha, ou separados por vírgula)"
        tk.Label(frame_lote, text=f"Baixar Múltiplos Vídeos {texto_ajuda}").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.text_videos = tk.Text(frame_lote, width=56, height=4)
        self.text_videos.grid(row=1, column=0, padx=5, pady=5)
        self._botao(frame_lote, "Baixar Múltiplos Vídeos", lambda: self._baixar_lote(self.text_videos, TIPO_VIDEO)) \
            .grid(row=2, column=0, sticky="w", padx=5, pady=5)

        tk.Label(frame_lote, text=f"Baixar Múltiplos Áudios {texto_ajuda}").grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.text_audios = tk.Text(frame_lote, width=56, height=4)
        self.text_audios.grid(row=1, column=1, padx=5, pady=5)
        self._botao(frame_lote, "Baixar Múltiplos Áudios", lambda: self._baixar_lote(self.text_audios, TIPO_AUDIO)) \
            .grid(row=2, column=1, sticky="w", padx=5, pady=5)

        frame_transcricao = tk.Frame(self.root)
        frame_transcricao.pack(pady=10)

        tk.Label(frame_transcricao, text="Escolha um arquivo de áudio para transcrição") \
            .grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.text_transcricao = tk.Text(frame_transcricao, width=100, height=5)
        self.text_transcricao.grid(row=1, column=0, padx=5, pady=5)
        self._botao(frame_transcricao, "Buscar arquivo e transcrever", self._transcrever) \
            .grid(row=2, column=0, sticky="w", padx=5, pady=5)

        self.progresso = ttk.Progressbar(frame_transcricao, orient="horizontal", length=800,
                                         mode="determinate", maximum=100)
        self.progresso.grid(row=3, column=0, padx=5, pady=5)
        self.label_status = tk.Label(frame_transcricao, text="")
        self.label_status.grid(row=4, column=0, padx=5, pady=5)

        frame_botoes = tk.Frame(self.root)
        frame_botoes.pack(pady=10)

        self.botao_cancelar = tk.Button(frame_botoes, text="Cancelar", command=self._cancelar)
        # Só aparece enquanto há tarefa em andamento.
        self.botao_tema = tk.Button(frame_botoes, text="Alternar Tema", command=self._alternar_tema)
        self.botao_tema.pack(side=tk.LEFT, padx=5, pady=5)
        self._frame_botoes = frame_botoes

    def _botao(self, pai, texto, comando):
        botao = tk.Button(pai, text=texto, command=comando)
        self._botoes_acao.append(botao)
        return botao

    # ------------------------------------------------------------------- tema

    def _alternar_tema(self):
        self._tema = "escuro" if self._tema == "azul" else "azul"
        self._aplicar_tema()

    def _aplicar_tema(self):
        cores = TEMAS[self._tema]

        def pintar(widget):
            if isinstance(widget, (tk.Frame, tk.Tk)):
                widget.config(bg=cores["fundo"])
            elif isinstance(widget, tk.Label):
                widget.config(bg=cores["fundo"], fg=cores["texto"])
            elif isinstance(widget, tk.Button):
                widget.config(bg=cores["botao"], fg="white", activebackground=cores["botao"])
            elif isinstance(widget, (tk.Entry, tk.Text)):
                widget.config(bg="white", fg="black", insertbackground="black")
            for filho in widget.winfo_children():
                pintar(filho)

        pintar(self.root)
        self.botao_cancelar.config(bg="#DC3545", activebackground="#DC3545")

    # ---------------------------------------------------- comunicação threads

    def _na_ui(self, funcao, *args):
        """Agenda ``funcao(*args)`` para rodar na thread principal (seguro a partir de qualquer thread)."""
        self._fila_ui.put((funcao, args))

    def _processar_fila_ui(self):
        # O reagendamento fica no fim (e no finally): assim nunca há timer pendente enquanto um
        # messagebox aberto aqui dentro roda seu laço de eventos, evitando execução reentrante.
        try:
            while True:
                try:
                    funcao, args = self._fila_ui.get_nowait()
                except queue.Empty:
                    break
                try:
                    funcao(*args)
                except Exception:  # noqa: BLE001 - um erro não pode parar a fila (botões ficariam travados)
                    traceback.print_exc()
        finally:
            self.root.after(INTERVALO_FILA_MS, self._processar_fila_ui)

    def _atualizar_progresso(self, percentual, prefixo=""):
        self.progresso["value"] = percentual
        self.label_status.config(text=f"{prefixo}{percentual:.1f}%")

    def _iniciar_tarefa(self, tarefa, alvo):
        """Trava os botões, mostra o 'Cancelar' e roda ``alvo`` numa thread de fundo."""
        if self._tarefa_atual is not None:
            messagebox.showwarning("Aguarde", "Já existe uma operação em andamento.")
            return
        self._tarefa_atual = tarefa
        for botao in self._botoes_acao:
            botao.config(state=tk.DISABLED)
        self.botao_cancelar.pack(side=tk.LEFT, padx=5, pady=5, before=self.botao_tema)
        self._thread_atual = threading.Thread(target=alvo, daemon=True)
        self._thread_atual.start()

    def _finalizar_tarefa(self):
        self._tarefa_atual = None
        for botao in self._botoes_acao:
            botao.config(state=tk.NORMAL)
        self.botao_cancelar.pack_forget()
        self.progresso["value"] = 0
        self.label_status.config(text="")

    def _cancelar(self):
        if self._tarefa_atual is not None:
            self._tarefa_atual.cancelar()
            self.label_status.config(text="Cancelando...")

    def _ao_fechar(self):
        # Guarda referências antes do diálogo: a tarefa pode terminar enquanto ele está aberto.
        tarefa, thread = self._tarefa_atual, self._thread_atual
        if tarefa is not None:
            if not messagebox.askokcancel("Sair", "Há uma operação em andamento. Deseja cancelar e sair?"):
                return
            tarefa.cancelar()
            if thread is not None:
                # Dá tempo para o download cancelado apagar o arquivo incompleto.
                thread.join(timeout=3)
        self.root.destroy()

    # --------------------------------------------------------------- download

    @staticmethod
    def _pasta_para(tipo):
        return config.PASTA_VIDEOS if tipo == TIPO_VIDEO else config.PASTA_AUDIOS

    def _baixar_unico(self, entry, tipo):
        url = entry.get().strip()
        if not e_url_youtube_valida(url):
            messagebox.showwarning("URL Inválida", "Por favor, insira um link válido do YouTube.")
            return

        downloader = Downloader()
        pasta = self._pasta_para(tipo)

        def trabalho():
            try:
                arquivo = downloader.baixar(url, tipo, pasta, lambda p: self._na_ui(self._atualizar_progresso, p))
                self._na_ui(self._sucesso_download, [arquivo], [], pasta)
            except DownloadCancelado:
                self._na_ui(messagebox.showinfo, "Cancelado", "O download foi cancelado.")
            except Exception as erro:  # noqa: BLE001 - mostrar qualquer falha ao usuário
                self._na_ui(messagebox.showerror, "Erro", f"Ocorreu um erro ao baixar: {erro}")
            finally:
                self._na_ui(self._finalizar_tarefa)

        self._iniciar_tarefa(downloader, trabalho)

    def _baixar_lote(self, text_widget, tipo):
        urls = extrair_urls(text_widget.get("1.0", tk.END))
        if not urls:
            messagebox.showwarning("Nenhum link", "Informe pelo menos um link do YouTube.")
            return
        invalidas = [u for u in urls if not e_url_youtube_valida(u)]
        if invalidas:
            messagebox.showwarning("URL Inválida", "Corrija os links inválidos:\n\n" + "\n".join(invalidas))
            return

        downloader = Downloader()
        pasta = self._pasta_para(tipo)
        item_atual = {"prefixo": ""}

        def ao_iniciar_item(indice, total, _url):
            item_atual["prefixo"] = f"Item {indice}/{total} — "

        def ao_progredir(p):
            self._na_ui(self._atualizar_progresso, p, item_atual["prefixo"])

        def trabalho():
            try:
                baixados, falhas = downloader.baixar_varios(urls, tipo, pasta, ao_progredir, ao_iniciar_item)
                self._na_ui(self._sucesso_download, baixados, falhas, pasta)
            except DownloadCancelado:
                self._na_ui(messagebox.showinfo, "Cancelado", "Os downloads restantes foram cancelados.")
            finally:
                self._na_ui(self._finalizar_tarefa)

        self._iniciar_tarefa(downloader, trabalho)

    def _sucesso_download(self, baixados, falhas, pasta):
        linhas = []
        if baixados:
            linhas.append(f"{len(baixados)} arquivo(s) salvo(s) em: {pasta}")
            linhas += [f"  • {os.path.basename(a)}" for a in baixados]
        if falhas:
            linhas.append(f"\n{len(falhas)} falha(s):")
            linhas += [f"  • {url}: {msg}" for url, msg in falhas]

        if falhas and not baixados:
            messagebox.showerror("Erro", "\n".join(linhas))
            return
        (messagebox.showwarning if falhas else messagebox.showinfo)("Download concluído", "\n".join(linhas))
        abrir_pasta(pasta)

    # ------------------------------------------------------------- transcrição

    def _transcrever(self):
        if not messagebox.askokcancel(
            "Atenção",
            "A transcrição usa o serviço online do Google, pode demorar e trechos com "
            "ruído podem ser perdidos. Deseja continuar?",
        ):
            return

        arquivo = filedialog.askopenfilename(
            title="Escolha um arquivo de áudio",
            filetypes=[("Arquivos de áudio", " ".join(config.EXTENSOES_AUDIO)), ("Todos os arquivos", "*.*")],
        )
        if not arquivo:
            return

        transcritor = Transcritor()

        def trabalho():
            try:
                texto, nao_entendidos = transcritor.transcrever(
                    arquivo, lambda p: self._na_ui(self._atualizar_progresso, p, "Transcrevendo: ")
                )
                self._na_ui(self._sucesso_transcricao, arquivo, texto, nao_entendidos)
            except TranscricaoCancelada:
                self._na_ui(messagebox.showinfo, "Cancelado", "A transcrição foi cancelada.")
            except ErroServicoTranscricao as erro:
                self._na_ui(messagebox.showerror, "Erro de conexão", str(erro))
            except Exception as erro:  # noqa: BLE001 - ex.: ffmpeg ausente, arquivo corrompido
                self._na_ui(messagebox.showerror, "Erro", f"Não foi possível transcrever: {erro}")
            finally:
                self._na_ui(self._finalizar_tarefa)

        self.text_transcricao.delete("1.0", tk.END)
        self._iniciar_tarefa(transcritor, trabalho)

    def _sucesso_transcricao(self, arquivo_origem, texto, nao_entendidos):
        if not texto:
            messagebox.showwarning("Sem resultado", "Nenhuma fala foi reconhecida neste áudio.")
            return

        self.text_transcricao.delete("1.0", tk.END)
        self.text_transcricao.insert(tk.END, texto)

        pasta = garantir_pasta(config.PASTA_TRANSCRICOES)
        destino = os.path.join(pasta, nome_arquivo_transcricao(arquivo_origem))
        with open(destino, "w", encoding="utf-8") as f:
            f.write(texto)

        aviso = f"\n\n{nao_entendidos} trecho(s) não puderam ser entendidos." if nao_entendidos else ""
        messagebox.showinfo("Sucesso", f"Transcrição salva em:\n{destino}{aviso}")
        abrir_pasta(pasta)


def main():
    """Ponto de entrada da aplicação gráfica."""
    config.configurar_ffmpeg_local()
    config.ocultar_janelas_de_console()
    root = tk.Tk()
    Aplicacao(root)
    root.mainloop()
