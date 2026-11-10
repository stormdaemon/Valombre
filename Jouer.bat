@echo off
chcp 65001 >nul
title Valombre - Les Eclats de l'Aube
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 goto nonode
node server.mjs --open
goto end
:nonode
where python >nul 2>nul
if errorlevel 1 goto nothing
echo Node.js est introuvable : utilisation de Python.
start "" "http://localhost:5173/"
python -m http.server 5173 --bind 127.0.0.1
goto end
:nothing
echo.
echo  Il faut Node.js (https://nodejs.org) pour lancer le jeu.
echo.
pause
:end
