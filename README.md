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

#### O que o instalador faz

| Etapa | Detalhe |
|---|---|
| Python | Instala o Python 3.12 só para o seu usuário, se ainda não tiver (via `winget` ou pelo site oficial python.org) |
| Programa | Copia o programa para `%LOCALAPPDATA%\Programs\AnalisadorYoutube` |
| Bibliotecas | Cria lá dentro um ambiente Python isolado com `pytubefix`, `SpeechRecognition` e `pydub` |
| ffmpeg | Baixa o ffmpeg (necessário para a transcrição) para dentro da pasta do programa |
| Atalhos | Cria **"Analisador YouTube"** na Área de Trabalho e no Menu Iniciar |
| Desinstalação | Registra em **Configurações → Aplicativos → Aplicativos instalados** |

O atalho abre o programa pelo `pythonw.exe` (o Python oficial, que tem assinatura digital) em vez de um `.exe` gerado na hora. Assim ele não é barrado pelo **Controle Inteligente de Aplicativos** do Windows 11, que bloqueia programas sem assinatura.

Para **atualizar** para uma versão nova, é só rodar o instalador de novo. Ele substitui o programa, atualiza as bibliotecas (importante para acompanhar as mudanças do YouTube) e mantém o ffmpeg já baixado.

#### Versão portátil (.exe) para distribuir — só para o desenvolvedor

Na pasta do projeto, rode `instalar.bat -GerarPortatil`. Além de instalar, ele gera `dist\AnalisadorYoutube-windows.zip`, com um `AnalisadorYoutube.exe` que roda sem instalar nada.

> Esse `.exe` não tem assinatura digital, então computadores com Controle Inteligente de Aplicativos ou com regras de segurança da empresa **vão bloqueá-lo**. Para esses casos, use o instalador normal.

#### Problemas comuns no Windows

| Mensagem | Solução |
|---|---|
| `a execução de scripts foi desabilitada neste sistema` | Use a **Opção 2** (`instalar.bat`), que já libera a execução só para o instalador. |
| `Nao foi possivel instalar o Python` | Instale o Python manualmente em [python.org/downloads](https://www.python.org/downloads/) marcando **"Add python.exe to PATH"** e rode o instalador de novo. |
| `uma política de controle de aplicativo bloqueou esse arquivo` | É o Windows barrando um programa sem assinatura digital. Se apareceu numa versão antiga do instalador (a que gerava `.exe`), **rode o instalador de novo**: a versão atual não usa mais `.exe`. Se aparecer **dentro do programa** ao transcrever, quem foi bloqueado é o ffmpeg; veja a linha abaixo. |
| Transcrição falha com "O Windows bloqueou um programa auxiliar" | O **Controle Inteligente de Aplicativos** bloqueou o ffmpeg. Abra **Segurança do Windows → Controle de aplicativos e navegador → Configurações do Controle Inteligente de Aplicativos** e veja se está **Ativado**. Desligar é opção sua: depois de desligado, ele não pode ser religado sem reinstalar o Windows. Em computador de empresa, peça à TI para liberar o `ffmpeg.exe`. Baixar vídeos e áudios continua funcionando normalmente. |
| Antivírus bloqueou o `AnalisadorYoutube.exe` (versão portátil) | Executáveis gerados pelo PyInstaller às vezes são confundidos com vírus (falso positivo). Libere o arquivo no antivírus ou use o instalador normal. |
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

O programa tem duas abas.

### Baixar vídeos e áudios
- Cole **um ou vários links de uma vez** (um por linha, ou separados por espaço/vírgula) e clique em **Adicionar**, ou use o botão **Colar**, que cola e adiciona direto.
- Os links vão para uma **lista**. Dá para remover os selecionados (tecla `Delete`) ou limpar tudo.
- Escolha **Vídeo** (MP4 em até 1080p, H.264, que abre em qualquer player) ou **Só o áudio** (M4A) e clique em **Baixar tudo**.

### Transcrever para texto
- Adicione **links do YouTube** e/ou **vários arquivos de áudio do computador de uma vez** (`mp3`, `mp4`, `m4a`, `wav`, `ogg`, `webm`; segure `Ctrl` para selecionar vários).
- Para links, **não é preciso baixar o áudio antes**. Se o vídeo tiver **legenda em português**, o texto sai na hora. Se não tiver, o programa baixa o áudio em segundo plano, transcreve e apaga o áudio.
- Cada transcrição vira um `.txt` com o título do vídeo (ou o nome do arquivo) e também aparece na tela, com o botão **Copiar texto**.

### Onde os arquivos ficam

Tudo fica na pasta **Downloads** do usuário:

```
Downloads/
└── Analisador YouTube/
    ├── Videos/
    ├── Audios/
    └── Transcricoes/
```

O botão **Abrir pasta dos arquivos** abre essa pasta.

### Em todas as operações
- Botão **Cancelar** interrompe de verdade e apaga o arquivo incompleto.
- Em listas, um item com problema não interrompe os outros. No final aparece um resumo, e **os itens que falharam continuam na lista** para tentar de novo.
- Mensagens de erro em português (vídeo privado, removido, com restrição de idade etc.).
- A janela não trava durante o trabalho. Tem modo claro e modo escuro.

> Transcrever áudio (arquivos e vídeos sem legenda) usa o serviço gratuito de reconhecimento de fala do Google: precisa de internet, é mais lento e trechos com muito ruído podem se perder (o programa avisa quantos). Legendas automáticas do YouTube costumam vir sem pontuação.

---

## Para desenvolvedores

### Estrutura

```
main.py                  # ponto de entrada
analisador/
  config.py              # pastas de saída (dentro de Downloads), idioma, ffmpeg embutido
  utils.py               # validação de URL, parsing de listas, nomes de arquivo
  downloader.py          # download com progresso e cancelamento (pytubefix); vídeo = imagem + áudio juntados no ffmpeg
  transcriber.py         # transcrição de arquivo de áudio em trechos (SpeechRecognition + pydub)
  transcricao_youtube.py # transcrição a partir do link: legenda do YouTube ou áudio temporário
  lote_transcricao.py    # fila de transcrição (links e arquivos misturados), salva cada .txt
  gui.py                 # interface Tkinter (threads se comunicam com a UI por fila)
tests/                   # testes unitários (pytest), sem acesso à rede
instalar.ps1 / .bat      # instalador Windows (gera .exe com PyInstaller)
instalar.sh              # instalador Linux/macOS
main.spec                # configuração do PyInstaller
```

### Rodando a partir do código

Requer Python 3.10+ com tkinter e o [ffmpeg](https://ffmpeg.org/download.html) no PATH.

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
- Escolha de qualidade do vídeo (hoje é sempre a melhor até 1080p)
- Conversão do áudio para MP3
- Escolha do idioma da transcrição na interface
- Histórico de downloads

### Veja mais

- [Portfólio](https://luizcarlos-cv.netlify.app/)
