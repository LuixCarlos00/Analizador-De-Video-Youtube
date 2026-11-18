# Analisador de Vídeo do YouTube

Aplicativo com interface gráfica para **baixar vídeos e áudios do YouTube** (um ou vários de uma vez) e **transcrever arquivos de áudio em texto**.

[![My Skills](https://skillicons.dev/icons?i=py,vscode)](https://skillicons.dev)

---

## Instalação (para quem não é desenvolvedor)

Um comando só: ele instala tudo o que falta (Python, ffmpeg, bibliotecas), cria o atalho na Área de Trabalho e já abre o programa.

### Windows (10 ou 11)

**Requisitos:** internet e uns 15 minutos na primeira vez. **Não** precisa ser administrador nem ter nada instalado antes.

#### Opção 1 — Um comando só (recomendado)

1. Aperte a tecla **Windows**, digite **`PowerShell`** e abra o **Windows PowerShell** (a janela azul).
2. Copie o comando abaixo, cole na janela (clique com o botão direito do mouse) e aperte **Enter**:

   ```powershell
   irm https://raw.githubusercontent.com/LuixCarlos00/Analizador-De-Video-Youtube/main/instalar.ps1 | iex
   ```

3. Espere. O texto vai mostrando cada etapa (`==> ...`). **Não feche a janela** até aparecer:

   ```
   Pronto! Abra pelo atalho 'Analisador YouTube' na Area de Trabalho.
   ```

   O programa abre sozinho no final.

#### Opção 2 — Baixando o projeto

1. Nesta página do GitHub, clique em **Code → Download ZIP**.
2. Clique com o botão direito no `.zip` baixado → **Extrair tudo...** → **Extrair**.
3. Dentro da pasta extraída, dê **duplo clique em `instalar.bat`**.
4. Se aparecer a tela azul **"O Windows protegeu o computador"**, clique em **Mais informações → Executar assim mesmo**. Isso acontece com qualquer script baixado da internet que não tem assinatura digital.
5. Espere até aparecer `Pronto!` e aperte qualquer tecla para fechar.

Nessa opção, o instalador também gera `dist\AnalisadorYoutube-windows.zip`. É uma **versão portátil** que você pode mandar para outra pessoa: ela só precisa extrair e abrir o `AnalisadorYoutube.exe`, sem instalar nada.

#### O que o instalador faz

| Etapa | Detalhe |
|---|---|
| Python | Instala o Python 3.12 só para o seu usuário, se ainda não tiver (via `winget` ou pelo site oficial python.org) |
| Bibliotecas | Cria um ambiente isolado e instala `pytubefix`, `SpeechRecognition` e `pydub` |
| Programa | Gera o `AnalisadorYoutube.exe` e instala em `%LOCALAPPDATA%\Programs\AnalisadorYoutube` |
| ffmpeg | Baixa o ffmpeg (necessário para a transcrição) para dentro da pasta do programa |
| Atalhos | Cria **"Analisador YouTube"** na Área de Trabalho e no Menu Iniciar |
| Desinstalação | Registra em **Configurações → Aplicativos → Aplicativos instalados** |

Para **atualizar** para uma versão nova, é só rodar o instalador de novo. Ele substitui o programa e mantém o ffmpeg já baixado.

#### Problemas comuns no Windows

| Mensagem | Solução |
|---|---|
| `a execução de scripts foi desabilitada neste sistema` | Use a **Opção 2** (`instalar.bat`), que já libera a execução só para o instalador. |
| `Nao foi possivel instalar o Python` | Instale o Python manualmente em [python.org/downloads](https://www.python.org/downloads/) marcando **"Add python.exe to PATH"** e rode o instalador de novo. |
| Antivírus bloqueou o `AnalisadorYoutube.exe` | Executáveis gerados pelo PyInstaller às vezes são confundidos com vírus (falso positivo). Libere o arquivo no antivírus. |
| Erro ao baixar (`HTTP 403`, `bot`, etc.) | O YouTube muda com frequência. Rode o instalador de novo para atualizar a biblioteca `pytubefix`. |
| Qualquer outro `ERRO:` em vermelho | Tire um print da janela e envie para o desenvolvedor. |

### Linux / macOS

Abra o terminal e cole:

```bash
curl -fsSL https://raw.githubusercontent.com/LuixCarlos00/Analizador-De-Video-Youtube/main/instalar.sh | bash
```

Depois abra **"Analisador YouTube"** pelo menu de aplicativos ou pela Área de Trabalho (no terminal: `analisador-youtube`).
Pode pedir sua senha para instalar `python3-tk` e `ffmpeg`. No macOS é preciso ter o [Homebrew](https://brew.sh).

### Desinstalar

- **Windows:** Configurações → Aplicativos instalados → *Analisador YouTube* → Desinstalar
- **Linux/macOS:** `bash instalar.sh --desinstalar`

Seus downloads e transcrições **não** são apagados.

---

## Funcionalidades

| Função | Onde salva |
|---|---|
| Baixar vídeo (maior resolução com áudio embutido, até 720p) | `~/Videos_Downloads` |
| Baixar só o áudio (formato `.m4a`) | `~/Audios_Downloads` |
| Baixar vários vídeos/áudios (um link por linha ou separados por vírgula) | mesmas pastas |
| Transcrever áudio (`mp3`, `mp4`, `m4a`, `wav`, `ogg`, `webm`) para texto em português | `~/Transcricoes` |

- Botão **Cancelar** interrompe de verdade o download/transcrição e apaga o arquivo incompleto.
- Em lotes, um link com problema não interrompe os outros; no final aparece o resumo do que deu certo e do que falhou.
- A janela não trava durante downloads e transcrições.
- Botão para alternar tema (azul/escuro).

> A transcrição usa o serviço gratuito de reconhecimento de fala do Google, então precisa de internet. Trechos com muito ruído podem não ser reconhecidos (o programa avisa quantos).

---

## Para desenvolvedores

### Estrutura

```
main.py                  # ponto de entrada
analisador/
  config.py              # pastas de saída, idioma, ffmpeg embutido
  utils.py               # validação de URL, parsing de listas, nomes de arquivo
  downloader.py          # download com progresso e cancelamento (pytubefix)
  transcriber.py         # transcrição em trechos (SpeechRecognition + pydub)
  gui.py                 # interface Tkinter (threads se comunicam com a UI por fila)
tests/                   # testes unitários (pytest), sem acesso à rede
instalar.ps1 / .bat      # instalador Windows (gera .exe com PyInstaller)
instalar.sh              # instalador Linux/macOS
main.spec                # configuração do PyInstaller
```

### Rodando a partir do código

Requer Python 3.9+ com tkinter e o [ffmpeg](https://ffmpeg.org/download.html) no PATH.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python main.py
```

### Testes

```bash
python -m pytest
```

### Gerar o executável manualmente

```bash
pyinstaller main.spec --noconfirm
```

O resultado fica em `dist/AnalisadorYoutube/`. No Windows, o `instalar.ps1` faz isso e ainda instala.

---

## Ideias para o futuro

- Download de playlists inteiras
- Escolha de qualidade do vídeo (acima de 720p, juntando vídeo e áudio com ffmpeg)
- Conversão do áudio para MP3
- Escolha do idioma da transcrição na interface
- Histórico de downloads

### Veja mais

- [Portfólio](https://luizcarlos-cv.netlify.app/)
