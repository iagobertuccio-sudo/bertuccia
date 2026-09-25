@echo off
echo Criando estrutura do projeto BertuccIA...

mkdir src\collectors
mkdir src\engine
mkdir src\messaging
mkdir src\utils
mkdir data\raw
mkdir data\processed
mkdir database
mkdir logs
mkdir tests

type nul > src\collectors\.gitkeep
type nul > src\engine\.gitkeep
type nul > src\messaging\.gitkeep
type nul > src\utils\.gitkeep
type nul > data\raw\.gitkeep
type nul > data\processed\.gitkeep
type nul > database\.gitkeep
type nul > logs\.gitkeep
type nul > tests\.gitkeep

echo Estrutura criada com sucesso!
pause
