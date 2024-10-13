## Projeto de Download e Transcrição de Vídeos e Áudios do YouTube

Este projeto é uma aplicação GUI desenvolvida em Python que permite baixar vídeos e áudios do YouTube e realizar a transcrição de áudios em texto.
A aplicação utiliza diversas bibliotecas como pytube, tkinter , speech_recognition, e pydub para oferecer uma interface amigável e funcionalidades robustas.
Abaixo estão os principais componentes e funcionalidades do projeto.

## Ferramentas Utilizadas

[![My Skills](https://skillicons.dev/icons?i=py,vscode)](https://skillicons.dev)

# Linguagem de Programação: Python

## Bibliotecas Utilizadas
Para executar este projeto, você precisará instalar as seguintes bibliotecas:

- pytubefix : Esta biblioteca parece ser uma modificação do pytube, que é usado para baixar vídeos do YouTube.
- tkinter: Para a interface gráfica.
- speech_recognition: Para transcrição de áudio.
- pydub: Para manipulação de arquivos de áudio.
 
 
  
## Descrição do Projeto
Este projeto é uma aplicação GUI desenvolvida em Python que permite baixar vídeos e áudios do YouTube e realizar a transcrição de áudios em texto. 
A aplicação utiliza diversas bibliotecas como pytube, tkinter,   speech_recognition, e pydub para oferecer uma interface amigável e funcionalidades robustas. 
Abaixo estão os principais componentes e funcionalidades do projeto.

## Funcionalidades

* Download de Vídeos do YouTube
  * Usuários podem inserir um link de vídeo do YouTube e baixar o vídeo em alta resolução.
  * Os vídeos são salvos na pasta "Videos_Downloads" no diretório do usuário.
  
* Download de Áudios do YouTube
   * Permite baixar apenas o áudio dos vídeos do YouTube.
   * Os áudios são salvos na pasta "Audios_Downloads" no diretório do usuário.


* Download de Múltiplos Vídeos e Áudios
  * Suporte para baixar múltiplos vídeos e áudios a partir de uma lista de URLs separadas por vírgulas.

    
* Transcrição de Áudios
  * Transcreve arquivos de áudio (MP3, MP4, WAV) em texto utilizando a biblioteca speech_recognition.
  * Os arquivos de áudio são convertidos para o formato WAV, divididos em partes menores para processamento, e então transcritos.
    
* Interface Gráfica
  * Desenvolvida com tkinter, a interface gráfica permite fácil interação do usuário com a aplicação.
  * Modo escuro disponível para melhor visualização.
 
    
## Instruções para Execução
* Clone este repositório:


``` 
git clone https://github.com/LuixCarlos00/Analizador-De-Video-Youtube.git
cd Analizador-De-Video-Youtub
````
 

### Passo 1 Criar um Ambiente Virtual (opcional, mas recomendado)
* Criar um ambiente virtual ajuda a gerenciar dependências específicas do projeto.
``` 
python -m venv myenv
myenv\Scripts\activate   
```

### Passo 2 Instalação das Dependências
* Crie um arquivo chamado requirements.txt na pasta do seu projeto e adicione as seguintes linhas:
```
pytube
SpeechRecognition
pydub

```

 ## Instalar as Dependências:
* Use o pip para instalar todas as dependências listadas no requirements.txt.
``` 
pip install -r requirements.txt
```

# Instalar ffmpeg
> [!IMPORTANT]
> pydub requer ffmpeg para manipulação de áudio. Instale ffmpeg conforme as instruções específicas para o seu sistema operacional.
* Windows: Baixe o executável de ffmpeg.org e adicione o diretório binário ao PATH do sistema.

### Passo 3: Código Fonte 
- Executar o Código Fonte:

```
python main.py

```
### Veja mais:
 - [link](http://localhost:4200/#/)

### Sinta se a vontade para melhorar e acrecentar funionalidades ao projeto. :rocket:
  
### Algumas funionalidades possiveis são :
    
  - Download de Playlists:
    * Permitir o download de todos os vídeos de uma playlist do YouTube.

  - Conversão de Formatos de Áudio/Vídeo:
     * Adicionar a capacidade de converter arquivos de áudio e vídeo para diferentes formatos (e.g., MP4, MP3, WAV).

  - Opções de Qualidade de Download:
     * Permitir que o usuário escolha a qualidade do vídeo ou áudio a ser baixado.

  - Histórico de Downloads:
    * Manter um registro dos vídeos e áudios baixados, permitindo que os usuários vejam e acessem downloads anteriores.

  - Integração com Serviços de Nuvem:
    * Adicionar a opção de enviar automaticamente os arquivos baixados para serviços de nuvem como Google Drive, Dropbox, etc.

  - Controle de Erros Aprimorado:
    * Implementar um sistema de log para capturar e registrar erros detalhadamente.

  - Interface Multilingue:
    * Adicionar suporte a múltiplos idiomas na interface gráfica.



