@echo off
rem Duplo clique aqui para instalar o Analisador YouTube no Windows.
rem Ele apenas chama o instalar.ps1 liberando a execucao de scripts so para este comando.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1" %*
pause
