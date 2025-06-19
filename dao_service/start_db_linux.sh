#!/usr/bin/env bash

# -----------------------------
# Параметры подключения
PORT=27017
BIND_IP="localhost"
# -----------------------------

# Пытаемся найти mongod в PATH
MONGOD_BIN=$(command -v mongod)

# Если не нашли, пробуем стандартные пути
if [ -z "$MONGOD_BIN" ]; then
  for p in /usr/bin/mongod /usr/local/bin/mongod /snap/bin/mongod; do
    if [ -x "$p" ]; then
      MONGOD_BIN="$p"
      break
    fi
  done
fi

# Если так и не нашли — выходим с ошибкой
if [ -z "$MONGOD_BIN" ]; then
  echo "Ошибка: исполняемый файл mongod не найден." >&2
  exit 1
fi

# Определяем каталог скрипта
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Каталог для хранения данных и логов
DATA_DIR="$SCRIPT_DIR/MongoData"
LOG_FILE="$SCRIPT_DIR/DATABASE.log"

# Создаём каталог, если его нет
mkdir -p "$DATA_DIR"

# Запуск mongod в foreground с перенаправлением вывода в лог
exec "$MONGOD_BIN" \
  --bind_ip "$BIND_IP" \
  --port "$PORT" \
  --dbpath "$DATA_DIR" \
   >"$LOG_FILE" 2>&1 &
