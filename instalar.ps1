<#
.SYNOPSIS
    Instalador "um comando so" do Analisador de Video do YouTube para Windows.

.DESCRIPTION
    1. Baixa o codigo do GitHub (se o script foi rodado fora da pasta do projeto).
    2. Instala o Python (se faltar) - via winget ou instalador oficial do python.org.
    3. Cria um ambiente virtual isolado e instala as dependencias.
    4. Gera o executavel com o PyInstaller.
    5. Instala em %LOCALAPPDATA%\Programs\AnalisadorYoutube, baixa o ffmpeg para dentro dele,
       cria atalhos na Area de Trabalho e no Menu Iniciar e registra em "Aplicativos instalados".
    6. Gera dist\AnalisadorYoutube-windows.zip (versao portatil para compartilhar).

    Nao precisa de administrador: tudo e instalado na pasta do usuario.

.EXAMPLE
    # Sem baixar nada antes (um comando so, no PowerShell):
    irm https://raw.githubusercontent.com/LuixCarlos00/Analizador-De-Video-Youtube/main/instalar.ps1 | iex

    # Com o projeto ja baixado: duplo clique em instalar.bat

    # Desinstalar:
    powershell -ExecutionPolicy Bypass -File instalar.ps1 -Desinstalar
#>
param([switch]$Desinstalar)

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

function Parar-App {
    Get-Process -Name $NomeApp -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Milliseconds 500
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
# Retorna @{Exe=...; Args=@(...)} de um Python >= 3.9, ou $null.
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
        if ("$versao" -match 'Python 3\.(\d+)' -and [int]$Matches[1] -ge 9) { return $c }
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
function Criar-Atalhos([string]$exe) {
    $shell = New-Object -ComObject WScript.Shell
    foreach ($caminho in $Atalhos) {
        $atalho = $shell.CreateShortcut($caminho)
        $atalho.TargetPath = $exe
        $atalho.WorkingDirectory = Split-Path $exe
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
        "Get-Process -Name $(Q $NomeApp) | Stop-Process -Force",
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

    Etapa 'Criando ambiente isolado e instalando dependencias (pode levar alguns minutos)'
    $venv = Join-Path $origem '.venv'
    if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
        Executar $python.Exe (@($python.Args) + @('-m', 'venv', $venv))
    }
    $venvPython = Join-Path $venv 'Scripts\python.exe'
    Executar $venvPython @('-m', 'pip', 'install', '--upgrade', 'pip', '--quiet', '--disable-pip-version-check')
    Executar $venvPython @('-m', 'pip', 'install', '-r', (Join-Path $origem 'requirements.txt'), 'pyinstaller', '--quiet', '--disable-pip-version-check')
    Ok 'Dependencias instaladas'

    Etapa 'Gerando o executavel'
    Push-Location $origem
    try { Executar $venvPython @('-m', 'PyInstaller', 'main.spec', '--noconfirm', '--clean', '--log-level', 'WARN') }
    finally { Pop-Location }
    $pastaGerada = Join-Path $origem "dist\$NomeApp"
    Ok "Executavel gerado em $pastaGerada"

    Etapa "Instalando em $PastaInstalacao"
    Parar-App
    if (Test-Path $PastaInstalacao) {
        # Mantem o ffmpeg ja baixado em reinstalacoes (evita baixar ~100 MB de novo).
        Get-ChildItem $PastaInstalacao | Where-Object { $_.Name -ne 'ffmpeg' } | Remove-Item -Recurse -Force
    } else {
        New-Item -ItemType Directory -Path $PastaInstalacao | Out-Null
    }
    Copy-Item (Join-Path $pastaGerada '*') $PastaInstalacao -Recurse -Force
    Instalar-Ffmpeg $PastaInstalacao

    $exeInstalado = Join-Path $PastaInstalacao "$NomeApp.exe"
    Criar-Atalhos $exeInstalado
    Registrar-Desinstalador $exeInstalado

    if ($PSScriptRoot) {
        # So quando roda a partir do projeto (desenvolvedor): gera o .zip portatil para distribuir.
        Etapa 'Gerando versao portatil (.zip) para compartilhar'
        $zipFinal = Join-Path $origem "dist\$NomeApp-windows.zip"
        $itens = Get-ChildItem $PastaInstalacao | Where-Object { $_.Name -ne 'desinstalar.ps1' }
        Compress-Archive -Path $itens.FullName -DestinationPath $zipFinal -Force
        Ok $zipFinal
    }

    Write-Host "`nPronto! Abra pelo atalho '$NomeAtalho' na Area de Trabalho." -ForegroundColor Green
    Start-Process $exeInstalado
}
catch {
    Write-Host "`nERRO: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Se o problema continuar, envie esta mensagem para o desenvolvedor.' -ForegroundColor Red
    if ($PSScriptRoot) { exit 1 }   # via "irm | iex" nao fecha o terminal do usuario
}
finally {
    Restaurar-Preferencias
}
