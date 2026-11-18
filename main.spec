# -*- mode: python ; coding: utf-8 -*-
# Gera o executável com: pyinstaller main.spec --noconfirm
# (o instalar.ps1 já faz isso automaticamente).
import os

import nodejs_wheel
from PyInstaller.utils.hooks import collect_data_files

NOME_APP = "AnalisadorYoutube"

# speech_recognition usa o binário "flac" que vem dentro do pacote para enviar áudio ao Google;
# pytubefix traz arquivos auxiliares (JS do botguard). Sem isso o .exe quebra em tempo de execução.
datas = collect_data_files("speech_recognition") + collect_data_files("pytubefix")

# pytubefix executa o Node.js do pacote nodejs-wheel-binaries para decifrar a assinatura dos
# vídeos. O PyInstaller só leva os .py desse pacote; levamos só o executável do node
# (sem a pasta npm, que é grande e não é usada).
_pasta_node = os.path.dirname(nodejs_wheel.__file__)
binaries = [
    (os.path.join(_pasta_node, caminho), destino)
    for caminho, destino in (("node.exe", "nodejs_wheel"), (os.path.join("bin", "node"), "nodejs_wheel/bin"))
    if os.path.isfile(os.path.join(_pasta_node, caminho))
]
if not binaries:
    raise SystemExit("Executável do Node não encontrado em nodejs_wheel; reinstale as dependências.")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NOME_APP,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # app gráfico: não abre a janela preta do terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=NOME_APP,
)
