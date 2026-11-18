"""Interface gráfica (Tkinter + ttk).

Regra de ouro do Tkinter: widgets só podem ser alterados pela thread principal.
Por isso as threads de trabalho nunca tocam na interface: elas colocam funções
numa fila (``_fila_ui``) que a thread principal esvazia a cada 100 ms.
"""

import os
import queue
import sys
import threading
import tkinter as tk
import traceback
from tkinter import filedialog, font as tkfont, messagebox, ttk

from . import config
from .downloader import TIPO_AUDIO, TIPO_VIDEO, DownloadCancelado, Downloader, limpar_sobras_temporarias
from .lote_transcricao import TIPO_ARQUIVO, TIPO_LINK, ItemTranscricao, TranscritorEmLote
from .transcricao_youtube import ORIGEM_LEGENDA
from .transcriber import TranscricaoCancelada
from .utils import abrir_pasta, e_url_youtube_valida, extrair_urls, garantir_pasta

INTERVALO_FILA_MS = 100

PALETAS = {
    "claro": {
        "fundo": "#EEF1F6", "painel": "#FFFFFF", "texto": "#1F2937", "suave": "#6B7280",
        "destaque": "#2563EB", "destaque_ativo": "#1D4ED8", "borda": "#D1D5DB",
        "campo": "#FFFFFF", "selecao": "#DBEAFE", "perigo": "#DC2626", "perigo_ativo": "#B91C1C",
    },
    "escuro": {
        "fundo": "#0F172A", "painel": "#1E293B", "texto": "#F1F5F9", "suave": "#94A3B8",
        "destaque": "#3B82F6", "destaque_ativo": "#2563EB", "borda": "#334155",
        "campo": "#0F172A", "selecao": "#1E3A8A", "perigo": "#EF4444", "perigo_ativo": "#DC2626",
    },
}


class ListaDeItens(ttk.Frame):
    """Lista com barra de rolagem, botões de remover/limpar e contador de itens.

    Guarda o valor real de cada linha (link, caminho ou ``ItemTranscricao``) separado
    do texto exibido, e ignora itens repetidos.
    """

    def __init__(self, pai, nome_item="item", altura=8):
        """
        Args:
            pai (tk.Widget): widget pai.
            nome_item (str): usado no contador (ex.: "link" -> "3 link(s) na lista").
            altura (int): quantidade de linhas visíveis.
        """
        super().__init__(pai, style="Painel.TFrame")
        self._valores = []
        self._nome_item = nome_item
        self.bloqueada = False  # durante uma operação a lista não pode ser alterada pelo usuário

        self.listbox = tk.Listbox(self, height=altura, selectmode=tk.EXTENDED, activestyle="none",
                                  relief=tk.FLAT, borderwidth=0, highlightthickness=1)
        rolagem = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=rolagem.set)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        rolagem.grid(row=0, column=1, sticky="ns")
        self.listbox.bind("<Delete>", lambda _e: self.remover_selecionados())

        barra = ttk.Frame(self, style="Painel.TFrame")
        barra.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.botao_remover = ttk.Button(barra, text="Remover selecionados", command=self.remover_selecionados)
        self.botao_remover.pack(side=tk.LEFT)
        self.botao_limpar = ttk.Button(barra, text="Limpar lista", command=self.limpar)
        self.botao_limpar.pack(side=tk.LEFT, padx=6)
        self.contador = ttk.Label(barra, style="Dica.TLabel")
        self.contador.pack(side=tk.RIGHT)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._atualizar_contador()

    @property
    def valores(self):
        """list: cópia dos valores na ordem da lista."""
        return list(self._valores)

    @property
    def botoes(self):
        """list[ttk.Button]: botões que devem ser travados durante uma operação."""
        return [self.botao_remover, self.botao_limpar]

    def adicionar(self, valor, rotulo):
        """Adiciona um item, se ainda não estiver na lista.

        Args:
            valor (object): valor real do item.
            rotulo (str): texto exibido.

        Returns:
            bool: True se foi adicionado (False se já existia).
        """
        if self.bloqueada or valor in self._valores:
            return False
        self._valores.append(valor)
        self.listbox.insert(tk.END, f"  {rotulo}")  # Listbox não tem padding interno
        self.listbox.see(tk.END)
        self._atualizar_contador()
        return True

    def remover_selecionados(self):
        """Remove as linhas selecionadas."""
        if self.bloqueada:
            return
        for indice in sorted(self.listbox.curselection(), reverse=True):
            self.listbox.delete(indice)
            del self._valores[indice]
        self._atualizar_contador()

    def remover_valores(self, valores):
        """Remove da lista os valores indicados (ex.: os itens já processados com sucesso).

        Args:
            valores (Iterable): valores a remover; os que não estiverem na lista são ignorados.
        """
        remover = set(valores)
        for indice in range(len(self._valores) - 1, -1, -1):
            if self._valores[indice] in remover:
                self.listbox.delete(indice)
                del self._valores[indice]
        self._atualizar_contador()

    def limpar(self):
        """Esvazia a lista."""
        if self.bloqueada:
            return
        self.listbox.delete(0, tk.END)
        self._valores.clear()
        self._atualizar_contador()

    def _atualizar_contador(self):
        total = len(self._valores)
        self.contador.configure(
            text=f"{total} {self._nome_item}(s) na lista" if total else f"Nenhum {self._nome_item} na lista ainda")


class Aplicacao:
    """Janela principal com as abas Baixar e Transcrever."""

    def __init__(self, root):
        """
        Args:
            root (tk.Tk): janela raiz do Tkinter.
        """
        self.root = root
        self._fila_ui = queue.Queue()
        self._tarefa_atual = None  # Downloader ou TranscritorEmLote em execução (para cancelar)
        self._thread_atual = None
        self._tema = "claro"
        self._botoes_acao = []
        self._listas = []
        self._textos = []

        root.title("Analisador YouTube")
        root.geometry("960x780")
        root.minsize(820, 660)
        root.protocol("WM_DELETE_WINDOW", self._ao_fechar)

        self._configurar_fontes()
        self.estilo = ttk.Style(root)
        self.estilo.theme_use("clam")  # o tema "clam" aceita cores personalizadas em todos os sistemas

        self._montar_layout()
        self._aplicar_tema()
        self.root.after(INTERVALO_FILA_MS, self._processar_fila_ui)

    # ------------------------------------------------------------------ layout

    def _configurar_fontes(self):
        familia = "Segoe UI" if sys.platform == "win32" else tkfont.nametofont("TkDefaultFont").actual("family")
        for nome in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
            tkfont.nametofont(nome).configure(family=familia, size=10)
        self.fonte_titulo = tkfont.Font(family=familia, size=17, weight="bold")
        self.fonte_secao = tkfont.Font(family=familia, size=11, weight="bold")
        self.fonte_botao_destaque = tkfont.Font(family=familia, size=10, weight="bold")

    def _montar_layout(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        cabecalho = ttk.Frame(self.root, padding=(20, 16, 20, 8))
        cabecalho.grid(row=0, column=0, sticky="ew")
        cabecalho.columnconfigure(0, weight=1)
        ttk.Label(cabecalho, text="Analisador YouTube", style="Titulo.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(cabecalho, text="Baixe vídeos e áudios do YouTube e transforme falas em texto.",
                  style="Subtitulo.TLabel").grid(row=1, column=0, sticky="w")
        self.botao_tema = ttk.Button(cabecalho, command=self._alternar_tema)
        self.botao_tema.grid(row=0, column=1, rowspan=2, sticky="e")

        abas = ttk.Notebook(self.root)
        abas.grid(row=1, column=0, sticky="nsew", padx=20)
        abas.add(self._montar_aba_baixar(abas), text="  Baixar vídeos e áudios  ")
        abas.add(self._montar_aba_transcrever(abas), text="  Transcrever para texto  ")

        self._montar_rodape()

    def _secao(self, pai, linha, titulo, dica=None):
        ttk.Label(pai, text=titulo, style="Secao.TLabel").grid(row=linha, column=0, sticky="w", pady=(10, 0))
        if dica:
            ttk.Label(pai, text=dica, style="Dica.TLabel", wraplength=820, justify=tk.LEFT) \
                .grid(row=linha + 1, column=0, sticky="w", pady=(2, 6))

    def _campo_de_link(self, pai, linha, ao_adicionar, texto_botao="Adicionar"):
        """Campo para colar links + botões Colar e Adicionar. Retorna (frame, entry)."""
        frame = ttk.Frame(pai, style="Painel.TFrame")
        frame.grid(row=linha, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)
        entry = ttk.Entry(frame)
        entry.grid(row=0, column=0, sticky="ew", ipady=3)
        entry.bind("<Return>", lambda _e: ao_adicionar())
        self._botao(frame, "Colar", lambda: self._colar_e_adicionar(entry, ao_adicionar)) \
            .grid(row=0, column=1, padx=(8, 0))
        self._botao(frame, texto_botao, ao_adicionar).grid(row=0, column=2, padx=(8, 0))
        return frame, entry

    def _montar_aba_baixar(self, abas):
        aba = ttk.Frame(abas, style="Painel.TFrame", padding=18)
        aba.columnconfigure(0, weight=1)
        aba.rowconfigure(3, weight=1)

        self._secao(aba, 0, "1. Adicione os links",
                    "Cole um ou vários links de uma vez (um por linha, ou separados por espaço/vírgula) "
                    "e clique em Adicionar. O botão Colar já cola e adiciona.")
        _, self.entry_baixar = self._campo_de_link(aba, 2, self._adicionar_links_baixar)

        self.lista_baixar = ListaDeItens(aba, nome_item="link")
        self.lista_baixar.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        self._listas.append(self.lista_baixar)

        self._secao(aba, 4, "2. Escolha o formato")
        formatos = ttk.Frame(aba, style="Painel.TFrame")
        formatos.grid(row=5, column=0, sticky="w", pady=(4, 0))
        self.formato = tk.StringVar(value=TIPO_VIDEO)
        ttk.Radiobutton(formatos, text="Vídeo  (MP4, até 1080p)", value=TIPO_VIDEO, variable=self.formato,
                        style="Painel.TRadiobutton").pack(side=tk.LEFT)
        ttk.Radiobutton(formatos, text="Só o áudio  (M4A)", value=TIPO_AUDIO, variable=self.formato,
                        style="Painel.TRadiobutton").pack(side=tk.LEFT, padx=(24, 0))

        self._botao(aba, "Baixar tudo", self._baixar, destaque=True).grid(row=6, column=0, sticky="e", pady=(14, 0))
        return aba

    def _montar_aba_transcrever(self, abas):
        aba = ttk.Frame(abas, style="Painel.TFrame", padding=18)
        aba.columnconfigure(0, weight=1)
        aba.rowconfigure(4, weight=1)
        aba.rowconfigure(9, weight=2)

        self._secao(aba, 0, "1. Adicione links do YouTube e/ou arquivos de áudio",
                    "Cole links e clique em Adicionar, ou escolha vários arquivos de áudio do computador "
                    "de uma vez (segure Ctrl para selecionar mais de um).")
        frame_link, self.entry_transcrever = self._campo_de_link(
            aba, 2, self._adicionar_links_transcrever, texto_botao="Adicionar link")
        self._botao(frame_link, "Escolher arquivos de áudio...", self._escolher_arquivos) \
            .grid(row=0, column=3, padx=(8, 0))

        ttk.Frame(aba, style="Painel.TFrame", height=10).grid(row=3, column=0)
        self.lista_transcrever = ListaDeItens(aba, nome_item="item", altura=6)
        self.lista_transcrever.grid(row=4, column=0, sticky="nsew")
        self._listas.append(self.lista_transcrever)

        self._secao(aba, 5, "2. Opções",
                    "Arquivos de áudio e vídeos sem legenda usam o reconhecimento de voz do Google: "
                    "precisa de internet, é mais lento e trechos com ruído podem se perder.")
        self.usar_legendas = tk.BooleanVar(value=True)
        ttk.Checkbutton(aba, text="Usar a legenda do YouTube quando o vídeo tiver (muito mais rápido)",
                        variable=self.usar_legendas, style="Painel.TCheckbutton").grid(row=7, column=0, sticky="w")

        self._botao(aba, "Transcrever tudo", self._transcrever, destaque=True) \
            .grid(row=7, column=0, sticky="e")

        cabecalho_resultado = ttk.Frame(aba, style="Painel.TFrame")
        cabecalho_resultado.grid(row=8, column=0, sticky="ew", pady=(14, 4))
        ttk.Label(cabecalho_resultado, text="Resultado", style="Secao.TLabel").pack(side=tk.LEFT)
        ttk.Button(cabecalho_resultado, text="Copiar texto", command=self._copiar_resultado).pack(side=tk.RIGHT)

        frame_texto = ttk.Frame(aba, style="Painel.TFrame")
        frame_texto.grid(row=9, column=0, sticky="nsew")
        frame_texto.columnconfigure(0, weight=1)
        frame_texto.rowconfigure(0, weight=1)
        self.text_resultado = tk.Text(frame_texto, height=7, wrap=tk.WORD, relief=tk.FLAT, font="TkTextFont",
                                      borderwidth=0, highlightthickness=1, padx=8, pady=6)
        rolagem = ttk.Scrollbar(frame_texto, orient=tk.VERTICAL, command=self.text_resultado.yview)
        self.text_resultado.configure(yscrollcommand=rolagem.set)
        self.text_resultado.grid(row=0, column=0, sticky="nsew")
        rolagem.grid(row=0, column=1, sticky="ns")
        self._textos.append(self.text_resultado)
        return aba

    def _montar_rodape(self):
        rodape = ttk.Frame(self.root, padding=(20, 10, 20, 14))
        rodape.grid(row=2, column=0, sticky="ew")
        rodape.columnconfigure(0, weight=1)

        self.progresso = ttk.Progressbar(rodape, orient=tk.HORIZONTAL, mode="determinate", maximum=100)
        self.progresso.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.label_status = ttk.Label(rodape, text="Pronto.", style="Subtitulo.TLabel")
        self.label_status.grid(row=1, column=0, sticky="w", pady=(6, 0))

        self.botao_cancelar = ttk.Button(rodape, text="Cancelar", command=self._cancelar, style="Perigo.TButton")
        # O botão Cancelar só aparece (grid) enquanto há uma operação em andamento.
        ttk.Button(rodape, text="Abrir pasta dos arquivos", command=self._abrir_pasta_base) \
            .grid(row=1, column=2, sticky="e", pady=(6, 0))
        ttk.Label(rodape, text=f"Os arquivos são salvos em: {config.PASTA_BASE}", style="Subtitulo.TLabel") \
            .grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))

    def _botao(self, pai, texto, comando, destaque=False):
        botao = ttk.Button(pai, text=texto, command=comando, style="Destaque.TButton" if destaque else "TButton")
        self._botoes_acao.append(botao)
        return botao

    # -------------------------------------------------------------------- tema

    def _alternar_tema(self):
        self._tema = "escuro" if self._tema == "claro" else "claro"
        self._aplicar_tema()

    def _aplicar_tema(self):
        c = PALETAS[self._tema]
        e = self.estilo
        self.root.configure(bg=c["fundo"])

        e.configure(".", background=c["fundo"], foreground=c["texto"], bordercolor=c["borda"],
                    lightcolor=c["borda"], darkcolor=c["borda"], troughcolor=c["fundo"],
                    fieldbackground=c["campo"], selectbackground=c["selecao"], selectforeground=c["texto"])
        e.configure("TFrame", background=c["fundo"])
        e.configure("Painel.TFrame", background=c["painel"])
        e.configure("TLabel", background=c["fundo"], foreground=c["texto"])
        e.configure("Titulo.TLabel", background=c["fundo"], font=self.fonte_titulo)
        e.configure("Subtitulo.TLabel", background=c["fundo"], foreground=c["suave"])
        e.configure("Secao.TLabel", background=c["painel"], font=self.fonte_secao)
        e.configure("Dica.TLabel", background=c["painel"], foreground=c["suave"])

        e.configure("TButton", padding=(12, 6), background=c["painel"], foreground=c["texto"])
        e.map("TButton", background=[("disabled", c["fundo"]), ("active", c["selecao"])],
              foreground=[("disabled", c["suave"])])
        e.configure("Destaque.TButton", padding=(22, 8), background=c["destaque"], foreground="white",
                    bordercolor=c["destaque"], font=self.fonte_botao_destaque)
        e.map("Destaque.TButton", background=[("disabled", c["borda"]), ("active", c["destaque_ativo"])],
              foreground=[("disabled", c["suave"])])
        e.configure("Perigo.TButton", background=c["perigo"], foreground="white", bordercolor=c["perigo"])
        e.map("Perigo.TButton", background=[("active", c["perigo_ativo"])])

        e.configure("TEntry", fieldbackground=c["campo"], foreground=c["texto"], insertcolor=c["texto"], padding=5)
        e.map("TEntry", bordercolor=[("focus", c["destaque"])])
        for estilo in ("Painel.TRadiobutton", "Painel.TCheckbutton"):
            e.configure(estilo, background=c["painel"], foreground=c["texto"], indicatorbackground=c["campo"],
                        indicatorforeground=c["destaque"])
            e.map(estilo, background=[("active", c["painel"])], indicatorbackground=[("selected", c["campo"])])

        e.configure("TNotebook", background=c["fundo"], borderwidth=0, tabmargins=(0, 0, 0, 0))
        e.configure("TNotebook.Tab", padding=(16, 8), background=c["fundo"], foreground=c["suave"],
                    font=self.fonte_secao)
        e.map("TNotebook.Tab", background=[("selected", c["painel"])], foreground=[("selected", c["texto"])],
              expand=[("selected", (0, 0, 0, 0))])
        e.configure("Horizontal.TProgressbar", background=c["destaque"], troughcolor=c["borda"],
                    bordercolor=c["borda"], thickness=10)
        e.configure("Vertical.TScrollbar", background=c["painel"], troughcolor=c["fundo"], arrowcolor=c["suave"])

        # Widgets tk "clássicos" (Listbox/Text) não seguem o ttk.Style: cores aplicadas direto.
        for lista in self._listas:
            lista.listbox.configure(bg=c["campo"], fg=c["texto"], selectbackground=c["selecao"],
                                    selectforeground=c["texto"], highlightbackground=c["borda"],
                                    highlightcolor=c["destaque"])
        for texto in self._textos:
            texto.configure(bg=c["campo"], fg=c["texto"], insertbackground=c["texto"],
                            highlightbackground=c["borda"], highlightcolor=c["destaque"],
                            selectbackground=c["selecao"], selectforeground=c["texto"])

        self.botao_tema.configure(text="Modo escuro" if self._tema == "claro" else "Modo claro")

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

    def _mostrar_progresso(self, percentual, texto):
        self.progresso["value"] = percentual
        self.label_status.configure(text=f"{texto}{percentual:.0f}%")

    def _iniciar_tarefa(self, tarefa, alvo):
        """Trava os botões, mostra o Cancelar e roda ``alvo`` numa thread de fundo."""
        if self._tarefa_atual is not None:
            messagebox.showwarning("Aguarde", "Já existe uma operação em andamento.")
            return
        self._tarefa_atual = tarefa
        for botao in self._botoes_acao + [b for lista in self._listas for b in lista.botoes]:
            botao.state(["disabled"])
        for lista in self._listas:
            lista.bloqueada = True  # também vale para Enter no campo e Delete na lista
        self.botao_cancelar.grid(row=1, column=1, sticky="e", padx=8, pady=(6, 0))
        self._thread_atual = threading.Thread(target=alvo, daemon=True)
        self._thread_atual.start()

    def _finalizar_tarefa(self):
        self._tarefa_atual = None
        for botao in self._botoes_acao + [b for lista in self._listas for b in lista.botoes]:
            botao.state(["!disabled"])
        for lista in self._listas:
            lista.bloqueada = False
        self.botao_cancelar.grid_remove()
        self.progresso["value"] = 0
        self.label_status.configure(text="Pronto.")

    def _cancelar(self):
        if self._tarefa_atual is not None:
            self._tarefa_atual.cancelar()
            self.label_status.configure(text="Cancelando...")

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

    def _progresso_em_lote(self, prefixo_etapa=""):
        """Cria callbacks (ao_iniciar_item, ao_status, ao_progredir) que mostram o progresso geral do lote."""
        estado = {"indice": 1, "total": 1, "etapa": prefixo_etapa}

        def ao_iniciar_item(indice, total, _item):
            estado["indice"], estado["total"] = indice, total

        def ao_status(texto):
            estado["etapa"] = texto

        def ao_progredir(percentual_item):
            geral = ((estado["indice"] - 1) + percentual_item / 100) / estado["total"] * 100
            texto = f"Item {estado['indice']} de {estado['total']}  ·  {estado['etapa']}"
            self._na_ui(self._mostrar_progresso, geral, texto)

        return ao_iniciar_item, ao_status, ao_progredir

    # ------------------------------------------------------- adicionar itens

    def _colar_e_adicionar(self, entry, ao_adicionar):
        try:
            conteudo = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showinfo("Nada para colar", "A área de transferência está vazia.")
            return
        entry.delete(0, tk.END)
        entry.insert(0, conteudo)
        ao_adicionar()

    def _ler_links(self, entry):
        """Lê o campo, separa os links e devolve só os válidos (avisando sobre os inválidos)."""
        urls = extrair_urls(entry.get())
        if not urls:
            messagebox.showwarning("Nenhum link", "Cole pelo menos um link do YouTube no campo.")
            return []
        invalidas = [u for u in urls if not e_url_youtube_valida(u)]
        if invalidas:
            messagebox.showwarning("Links ignorados",
                                   "Estes textos não são links de vídeo do YouTube e foram ignorados:\n\n"
                                   + "\n".join(invalidas[:10]))
        entry.delete(0, tk.END)
        return [u for u in urls if e_url_youtube_valida(u)]

    def _adicionar_links_baixar(self):
        if self._tarefa_atual is not None:
            return
        for url in self._ler_links(self.entry_baixar):
            self.lista_baixar.adicionar(url, url)

    def _adicionar_links_transcrever(self):
        if self._tarefa_atual is not None:
            return
        for url in self._ler_links(self.entry_transcrever):
            item = ItemTranscricao(TIPO_LINK, url)
            self.lista_transcrever.adicionar(item, item.rotulo)

    def _escolher_arquivos(self):
        arquivos = filedialog.askopenfilenames(
            title="Escolha um ou mais arquivos de áudio",
            filetypes=[("Arquivos de áudio", " ".join(config.EXTENSOES_AUDIO)), ("Todos os arquivos", "*.*")],
        )
        for caminho in arquivos:
            item = ItemTranscricao(TIPO_ARQUIVO, caminho)
            self.lista_transcrever.adicionar(item, item.rotulo)

    # --------------------------------------------------------------- download

    def _baixar(self):
        urls = self.lista_baixar.valores
        if not urls:
            messagebox.showwarning("Lista vazia", "Adicione pelo menos um link à lista antes de baixar.")
            return

        tipo = self.formato.get()  # lido aqui: variáveis Tk só na thread principal
        pasta = config.PASTA_VIDEOS if tipo == TIPO_VIDEO else config.PASTA_AUDIOS
        downloader = Downloader()
        ao_iniciar_item, _, ao_progredir = self._progresso_em_lote("Baixando: ")

        def trabalho():
            try:
                baixados, falhas = downloader.baixar_varios(urls, tipo, pasta, ao_progredir, ao_iniciar_item)
                self._na_ui(self._concluir_download, baixados, falhas, pasta)
            except DownloadCancelado as cancelamento:
                # O que já tinha sido salvo antes do cancelamento sai da lista.
                self._na_ui(self.lista_baixar.remover_valores, [url for url, _ in cancelamento.baixados])
                salvos = len(cancelamento.baixados)
                extra = f"\n\n{salvos} arquivo(s) já tinham sido salvos em:\n{pasta}" if salvos else ""
                self._na_ui(messagebox.showinfo, "Cancelado", f"O download foi cancelado.{extra}")
            finally:
                self._na_ui(self._finalizar_tarefa)

        self._iniciar_tarefa(downloader, trabalho)

    def _concluir_download(self, baixados, falhas, pasta):
        # Tira da lista o que deu certo; o que falhou fica para tentar de novo.
        self.lista_baixar.remover_valores([url for url, _ in baixados])

        linhas = []
        if baixados:
            linhas.append(f"{len(baixados)} arquivo(s) salvo(s) em:\n{pasta}\n")
            linhas += [f"  • {os.path.basename(arquivo)}" for _, arquivo in baixados[:15]]
            if len(baixados) > 15:
                linhas.append(f"  ... e mais {len(baixados) - 15}")
        if falhas:
            linhas.append(f"\n{len(falhas)} falha(s) (continuam na lista para tentar de novo):")
            linhas += [f"  • {url}: {msg}" for url, msg in falhas[:10]]

        if falhas and not baixados:
            messagebox.showerror("Não foi possível baixar", "\n".join(linhas))
            return
        (messagebox.showwarning if falhas else messagebox.showinfo)("Download concluído", "\n".join(linhas))
        abrir_pasta(pasta)

    # ------------------------------------------------------------- transcrição

    def _transcrever(self):
        itens = self.lista_transcrever.valores
        if not itens:
            messagebox.showwarning("Lista vazia",
                                   "Adicione pelo menos um link ou arquivo de áudio à lista antes de transcrever.")
            return

        usar_legendas = self.usar_legendas.get()  # lido aqui: variáveis Tk só na thread principal
        lote = TranscritorEmLote(config.PASTA_TRANSCRICOES)
        ao_iniciar_item, ao_status, ao_progredir = self._progresso_em_lote()

        def trabalho():
            try:
                sucessos, falhas = lote.transcrever(itens, usar_legendas, ao_progredir, ao_status, ao_iniciar_item)
                self._na_ui(self._concluir_transcricao, sucessos, falhas)
            except TranscricaoCancelada:
                self._na_ui(messagebox.showinfo, "Cancelado", "A transcrição foi cancelada.")
            finally:
                self._na_ui(self._finalizar_tarefa)

        self.text_resultado.delete("1.0", tk.END)
        self._iniciar_tarefa(lote, trabalho)

    def _concluir_transcricao(self, sucessos, falhas):
        self.lista_transcrever.remover_valores([sucesso.item for sucesso in sucessos])

        for sucesso in sucessos:
            r = sucesso.resultado
            self.text_resultado.insert(tk.END, f"===== {r.titulo} =====\n{r.texto}\n\n")

        linhas = []
        if sucessos:
            linhas.append(f"{len(sucessos)} transcrição(ões) salva(s) em:\n{config.PASTA_TRANSCRICOES}\n")
            for sucesso in sucessos[:15]:
                r = sucesso.resultado
                extra = f"; {r.nao_entendidos} trecho(s) não entendido(s)" if r.nao_entendidos else ""
                linhas.append(f"  • {os.path.basename(sucesso.arquivo_txt)}  ({r.detalhe or r.origem}{extra})")
            if any(s.resultado.origem == ORIGEM_LEGENDA and "autom" in s.resultado.detalhe.lower()
                   for s in sucessos):
                linhas.append("\nLegendas automáticas do YouTube costumam vir sem pontuação.")
        if falhas:
            linhas.append(f"\n{len(falhas)} falha(s) (continuam na lista para tentar de novo):")
            linhas += [f"  • {item.rotulo}: {msg}" for item, msg in falhas[:10]]

        if falhas and not sucessos:
            messagebox.showerror("Não foi possível transcrever", "\n".join(linhas))
            return
        (messagebox.showwarning if falhas else messagebox.showinfo)("Transcrição concluída", "\n".join(linhas))
        abrir_pasta(config.PASTA_TRANSCRICOES)

    def _copiar_resultado(self):
        texto = self.text_resultado.get("1.0", tk.END).strip()
        if not texto:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(texto)
        self.label_status.configure(text="Texto copiado para a área de transferência.")

    def _abrir_pasta_base(self):
        abrir_pasta(garantir_pasta(config.PASTA_BASE))


def main():
    """Ponto de entrada da aplicação gráfica."""
    config.configurar_ffmpeg_local()
    config.ocultar_janelas_de_console()
    limpar_sobras_temporarias()
    root = tk.Tk()
    Aplicacao(root)
    root.mainloop()
