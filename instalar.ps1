<#
.SYNOPSIS
    Instalador "um comando so" do Analisador de Video do YouTube para Windows.

.DESCRIPTION
    1. Baixa o codigo do GitHub (se o script foi rodado fora da pasta do projeto).
    2. Instala o Python (se faltar) - via winget ou instalador oficial do python.org.
    3. Copia o app para %LOCALAPPDATA%\Programs\AnalisadorYoutube, cria nele um ambiente
       Python isolado com as dependencias e baixa o ffmpeg para dentro dele.
    4. Cria atalhos na Area de Trabalho e no Menu Iniciar e registra em "Aplicativos instalados".

    O atalho abre o app pelo pythonw.exe (Python oficial, assinado digitalmente) em vez de um
    .exe gerado na hora: o Controle Inteligente de Aplicativos do Windows 11 e politicas de
    empresa (AppLocker/WDAC) bloqueiam executaveis sem assinatura nem reputacao.

    Com -GerarPortatil (uso do desenvolvedor), tambem gera dist\AnalisadorYoutube-windows.zip,
    uma versao .exe portatil feita com PyInstaller.

    Nao precisa de administrador: tudo e instalado na pasta do usuario.

.EXAMPLE
    # Sem baixar nada antes (um comando so, no PowerShell):
    irm https://raw.githubusercontent.com/LuixCarlos00/Analizador-De-Video-Youtube/main/instalar.ps1 | iex

    # Com o projeto ja baixado: duplo clique em instalar.bat

    # Desinstalar:
    powershell -ExecutionPolicy Bypass -File instalar.ps1 -Desinstalar

    # Gerar tambem o .exe portatil (.zip) para distribuir:
    powershell -ExecutionPolicy Bypass -File instalar.ps1 -GerarPortatil
#>
param([switch]$Desinstalar, [switch]$GerarPortatil)

# Via "irm | iex" o script roda no escopo da janela do usuario: guardamos as preferencias
# para restaura-las no final e nao alterar o comportamento do PowerShell dele.
$PreferenciasOriginais = @{ Erro = $ErrorActionPreference; Progresso = $ProgressPreference }
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # deixa o Invoke-WebRequest muito mais rapido
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

$NomeApp         = 'AnalisadorYoutube'
$NomeAtalho      = 'Analisador YouTube'
$Repositorio     = 'LuixCarlos00/Analizador-De-Video-Youtube'
$VersaoPython    = '3.12.8'
$UrlFfmpeg       = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
$PastaInstalacao = Join-Path $env:LOCALAPPDATA "Programs\$NomeApp"
$ChaveRegistro   = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$NomeApp"
$Atalhos = @(
    (Join-Path ([Environment]::GetFolderPath('Desktop'))  "$NomeAtalho.lnk"),
    (Join-Path ([Environment]::GetFolderPath('Programs')) "$NomeAtalho.lnk")
)

function Etapa([string]$texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }
function Ok([string]$texto)    { Write-Host "    $texto" -ForegroundColor Green }

# Roda um programa externo e para o script se ele falhar
# (no PowerShell 5, $ErrorActionPreference nao pega codigo de saida de .exe).
function Executar([string]$exe, [string[]]$argumentos) {
    $global:LASTEXITCODE = 0   # evita que um codigo antigo seja lido como resultado deste comando
    & $exe @argumentos
    if ($LASTEXITCODE -ne 0) { throw "Falhou: $exe $($argumentos -join ' ') (codigo $LASTEXITCODE)" }
}

# Acrescenta ao PATH desta janela as pastas novas do sistema/usuario (ex.: Python recem-instalado),
# sem apagar o que ja estava nele.
function Atualizar-Path {
    $atuais = $env:Path -split ';' | Where-Object { $_ }
    foreach ($escopo in 'Machine', 'User') {
        $valor = [Environment]::GetEnvironmentVariable('Path', $escopo)
        if (-not $valor) { continue }
        foreach ($pasta in ([Environment]::ExpandEnvironmentVariables($valor) -split ';')) {
            if ($pasta -and ($atuais -notcontains $pasta)) { $atuais += $pasta }
        }
    }
    $env:Path = $atuais -join ';'
}

# Fecha o app se estiver aberto (o pythonw.exe da pasta de instalacao, ou o .exe de versoes antigas),
# para os arquivos poderem ser substituidos.
function Parar-App {
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -and $_.Path.StartsWith($PastaInstalacao, [StringComparison]::OrdinalIgnoreCase) } |
        Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
}

# Mensagem clara quando o Windows bloqueia um programa (Smart App Control / AppLocker / WDAC).
function E-BloqueioDePolitica($erro) {
    return "$erro" -match 'pol.tica de controle de aplicativo|Application Control policy|4551'
}

# ------------------------------------------------------------------ desinstalar
function Desinstalar-App {
    Etapa "Desinstalando $NomeAtalho"
    Parar-App
    foreach ($atalho in $Atalhos) { Remove-Item $atalho -Force -ErrorAction SilentlyContinue }
    Remove-Item $ChaveRegistro -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $PastaInstalacao -Recurse -Force -ErrorAction SilentlyContinue
    Ok 'Removido. Seus videos, audios e transcricoes na pasta do usuario foram mantidos.'
}

function Restaurar-Preferencias {
    $script:ErrorActionPreference = $PreferenciasOriginais.Erro
    $script:ProgressPreference = $PreferenciasOriginais.Progresso
}

if ($Desinstalar) { try { Desinstalar-App } finally { Restaurar-Preferencias }; return }

# ------------------------------------------------------------- codigo-fonte
function Obter-CodigoFonte {
    if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot 'main.py'))) { return $PSScriptRoot }

    Etapa 'Baixando o codigo do GitHub'
    $temp = Join-Path $env:TEMP "$NomeApp-fonte"
    Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $temp | Out-Null
    $zip = Join-Path $temp 'fonte.zip'
    Invoke-WebRequest "https://github.com/$Repositorio/archive/refs/heads/main.zip" -OutFile $zip -UseBasicParsing
    Expand-Archive $zip -DestinationPath $temp -Force
    $pasta = Get-ChildItem $temp -Directory | Select-Object -First 1
    Ok "Codigo em $($pasta.FullName)"
    return $pasta.FullName
}

# ------------------------------------------------------------------- python
# Retorna @{Exe=...; Args=@(...)} de um Python >= 3.10, ou $null.
function Encontrar-Python {
    $candidatos = @(
        @{ Exe = 'py';     Args = @('-3.12') },
        @{ Exe = 'py';     Args = @('-3') },
        @{ Exe = 'python'; Args = @() },
        @{ Exe = (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'); Args = @() }
    )
    foreach ($c in $candidatos) {
        $argumentos = @($c.Args) + '--version'
        try { $versao = & $c.Exe @argumentos 2>&1 } catch { continue }
        # "python" pode ser o atalho da Microsoft Store, que nao imprime versao: o regex descarta.
        if ("$versao" -match 'Python 3\.(\d+)' -and [int]$Matches[1] -ge 10) { return $c }
    }
    return $null
}

function Instalar-Python {
    Etapa "Instalando Python $VersaoPython (somente para o seu usuario)"
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        & winget install -e --id Python.Python.3.12 --scope user --silent `
            --accept-package-agreements --accept-source-agreements
    }
    Atualizar-Path
    if (Encontrar-Python) { return }

    # Sem winget (ou se ele falhou): instalador oficial, silencioso, sem precisar de admin.
    $instalador = Join-Path $env:TEMP "python-$VersaoPython-amd64.exe"
    Invoke-WebRequest "https://www.python.org/ftp/python/$VersaoPython/python-$VersaoPython-amd64.exe" `
        -OutFile $instalador -UseBasicParsing
    # O instalador e um programa grafico: "&" nao esperaria ele terminar. Start-Process -Wait espera.
    $processo = Start-Process $instalador -Wait -PassThru -ArgumentList @(
        '/quiet', 'InstallAllUsers=0', 'PrependPath=1', 'Include_tcltk=1', 'Include_launcher=1')
    if ($processo.ExitCode -ne 0) { throw "O instalador do Python falhou (codigo $($processo.ExitCode))." }
    Atualizar-Path
}

# ------------------------------------------------------------------- ffmpeg
function Instalar-Ffmpeg([string]$destino) {
    $pastaBin = Join-Path $destino 'ffmpeg\bin'
    if (Test-Path (Join-Path $pastaBin 'ffmpeg.exe')) { Ok 'ffmpeg ja presente'; return }

    Etapa 'Baixando ffmpeg (necessario para converter audio na transcricao)'
    $temp = Join-Path $env:TEMP "$NomeApp-ffmpeg"
    Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $temp | Out-Null
    $zip = Join-Path $temp 'ffmpeg.zip'
    Invoke-WebRequest $UrlFfmpeg -OutFile $zip -UseBasicParsing
    Expand-Archive $zip -DestinationPath $temp -Force

    New-Item -ItemType Directory -Path $pastaBin -Force | Out-Null
    foreach ($exe in @('ffmpeg.exe', 'ffprobe.exe')) {
        $achado = Get-ChildItem $temp -Recurse -Filter $exe | Select-Object -First 1
        if (-not $achado) { throw "Nao encontrei $exe dentro do pacote do ffmpeg." }
        Copy-Item $achado.FullName $pastaBin -Force
    }
    Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue
    Ok "ffmpeg instalado em $pastaBin"
}

# ------------------------------------------------------------------ atalhos
function Criar-Atalhos([string]$exe, [string]$argumentos) {
    $shell = New-Object -ComObject WScript.Shell
    foreach ($caminho in $Atalhos) {
        $atalho = $shell.CreateShortcut($caminho)
        $atalho.TargetPath = $exe
        $atalho.Arguments = $argumentos
        $atalho.WorkingDirectory = $PastaInstalacao
        $atalho.Description = 'Baixar videos/audios do YouTube e transcrever audio'
        $atalho.Save()
    }
    Ok 'Atalhos criados na Area de Trabalho e no Menu Iniciar'
}

function Registrar-Desinstalador([string]$exe) {
    # Script de desinstalacao fica dentro da pasta do app, para o "Aplicativos instalados" do Windows.
    $desinstalador = Join-Path $PastaInstalacao 'desinstalar.ps1'
    # Aspas simples escapadas ('') para caminhos com apostrofo, ex.: C:\Users\D'Avila.
    function Q([string]$s) { "'" + $s.Replace("'", "''") + "'" }
    $linhas = @(
        "`$ErrorActionPreference = 'SilentlyContinue'",
        "`$pasta = $(Q $PastaInstalacao)",
        'Get-Process | Where-Object { $_.Path -and $_.Path.StartsWith($pasta, [StringComparison]::OrdinalIgnoreCase) } | Stop-Process -Force',
        'Start-Sleep -Milliseconds 500'
    )
    $linhas += $Atalhos | ForEach-Object { "Remove-Item -LiteralPath $(Q $_) -Force" }
    $linhas += @(
        "Remove-Item -LiteralPath $(Q $ChaveRegistro) -Recurse -Force",
        'Set-Location $env:TEMP',
        "Remove-Item -LiteralPath $(Q $PastaInstalacao) -Recurse -Force"
    )
    $linhas | Set-Content -Path $desinstalador -Encoding UTF8

    New-Item -Path $ChaveRegistro -Force | Out-Null
    $valores = @{
        DisplayName     = $NomeAtalho
        DisplayIcon     = $exe
        Publisher       = 'Luiz Carlos'
        InstallLocation = $PastaInstalacao
        UninstallString = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$desinstalador`""
    }
    foreach ($nome in $valores.Keys) {
        New-ItemProperty -Path $ChaveRegistro -Name $nome -Value $valores[$nome] -PropertyType String -Force | Out-Null
    }
    New-ItemProperty -Path $ChaveRegistro -Name NoModify -Value 1 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $ChaveRegistro -Name NoRepair -Value 1 -PropertyType DWord -Force | Out-Null
}

# ======================================================================= main
try {
    Write-Host "Instalador do $NomeAtalho" -ForegroundColor Yellow

    $origem = Obter-CodigoFonte

    Etapa 'Verificando Python'
    $python = Encontrar-Python
    if (-not $python) {
        Instalar-Python
        $python = Encontrar-Python
        if (-not $python) { throw 'Nao foi possivel instalar o Python. Instale manualmente em https://www.python.org e rode de novo.' }
    }
    Ok "Usando: $($python.Exe) $($python.Args -join ' ')"

    Etapa "Instalando em $PastaInstalacao"
    Parar-App
    if (Test-Path $PastaInstalacao) {
        # Reinstalacao: mantem o ffmpeg (~100 MB) e o ambiente Python ja criados; o resto e substituido
        # (inclusive o AnalisadorYoutube.exe e a pasta _internal de versoes antigas).
        Get-ChildItem $PastaInstalacao -Force | Where-Object { $_.Name -notin @('ffmpeg', '.venv') } |
            Remove-Item -Recurse -Force
    } else {
        New-Item -ItemType Directory -Path $PastaInstalacao | Out-Null
    }
    foreach ($item in @('analisador', 'main.py', 'requirements.txt')) {
        Copy-Item (Join-Path $origem $item) $PastaInstalacao -Recurse -Force
    }
    Get-ChildItem $PastaInstalacao -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force

    Etapa 'Criando ambiente isolado e instalando dependencias (pode levar alguns minutos)'
    $venv = Join-Path $PastaInstalacao '.venv'
    $venvPython = Join-Path $venv 'Scripts\python.exe'
    $venvPythonw = Join-Path $venv 'Scripts\pythonw.exe'
    if (-not (Test-Path $venvPythonw)) {
        Remove-Item $venv -Recurse -Force -ErrorAction SilentlyContinue
        Executar $python.Exe (@($python.Args) + @('-m', 'venv', $venv))
    }
    Executar $venvPython @('-m', 'pip', 'install', '--upgrade', 'pip', '--quiet', '--disable-pip-version-check')
    # --upgrade: reinstalar tambem atualiza a pytubefix, que precisa acompanhar as mudancas do YouTube.
    Executar $venvPython @('-m', 'pip', 'install', '--upgrade', '-r', (Join-Path $PastaInstalacao 'requirements.txt'),
                           '--quiet', '--disable-pip-version-check')
    Ok 'Dependencias instaladas'

    Instalar-Ffmpeg $PastaInstalacao

    $mainPy = Join-Path $PastaInstalacao 'main.py'
    Criar-Atalhos $venvPythonw "`"$mainPy`""
    Registrar-Desinstalador $venvPythonw

    if ($GerarPortatil) {
        Etapa 'Gerando versao portatil (.exe em .zip) com PyInstaller'
        Executar $venvPython @('-m', 'pip', 'install', 'pyinstaller', '--quiet', '--disable-pip-version-check')
        Push-Location $origem
        try { Executar $venvPython @('-m', 'PyInstaller', 'main.spec', '--noconfirm', '--clean', '--log-level', 'WARN') }
        finally { Pop-Location }
        $pastaGerada = Join-Path $origem "dist\$NomeApp"
        Copy-Item (Join-Path $PastaInstalacao 'ffmpeg') $pastaGerada -Recurse -Force
        $zipFinal = Join-Path $origem "dist\$NomeApp-windows.zip"
        Compress-Archive -Path (Join-Path $pastaGerada '*') -DestinationPath $zipFinal -Force
        Ok $zipFinal
        Ok 'Atencao: o .exe nao e assinado; computadores com Controle Inteligente de Aplicativos podem bloquea-lo.'
    }

    Write-Host "`nPronto! Abra pelo atalho '$NomeAtalho' na Area de Trabalho." -ForegroundColor Green
    try {
        Start-Process $venvPythonw -ArgumentList "`"$mainPy`"" -WorkingDirectory $PastaInstalacao
    }
    catch {
        # A instalacao terminou; so a abertura automatica falhou. Nao tratar como erro de instalacao.
        Write-Host "`nNao consegui abrir o programa automaticamente: $($_.Exception.Message)" -ForegroundColor Yellow
        if (E-BloqueioDePolitica $_) {
            Write-Host 'O Windows bloqueou o programa por uma politica de seguranca. Veja "Problemas comuns" no README.' -ForegroundColor Yellow
        }
    }
}
catch {
    Write-Host "`nERRO: $($_.Exception.Message)" -ForegroundColor Red
    if (E-BloqueioDePolitica $_) {
        Write-Host 'O Windows bloqueou um programa por uma politica de seguranca (Controle Inteligente de Aplicativos ou regra da empresa). Veja "Problemas comuns" no README.' -ForegroundColor Red
    } else {
        Write-Host 'Se o problema continuar, envie esta mensagem para o desenvolvedor.' -ForegroundColor Red
    }
    if ($PSScriptRoot) { exit 1 }   # via "irm | iex" nao fecha o terminal do usuario
}
finally {
    Restaurar-Preferencias
}
