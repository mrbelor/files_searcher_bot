#!/usr/bin/env bash

# -----------------------------
# Параметры подключения (редактируйте здесь)
PORT=27017
BIND_IP="localhost" # 127.0.0.1
# -----------------------------

# Автоматически определяем префикс Homebrew
BREW_HOME="$(brew --prefix)"
export BREW_HOME

# Путь к папке с mongo (Homebrew/bin)
MONGO_HOME="$BREW_HOME"

# Определяем каталог скрипта
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Директория для хранения данных
DATA_DIR="$SCRIPT_DIR/MongoData"

# Создаём каталог для данных, если его нет
mkdir -p "$DATA_DIR"

# Запуск mongod в foreground с кастомными портом и IP
exec "$MONGO_HOME/bin/mongod" \
  --bind_ip "$BIND_IP" \
  --port "$PORT" \
  --dbpath "$DATA_DIR"
