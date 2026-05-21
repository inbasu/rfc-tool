#!/bin/bash

# Директории
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_FILE="$SCRIPT_DIR/src/rfc.py"
TARGET_LINK="/usr/local/bin/rfc"


echo -e "Установка RFC Tool:"

# Проверяем существование исходника
if [ ! -f "$SOURCE_FILE" ]; then
    echo -e "Нет исходного файла: $SOURCE_FILE"
    echo -e "Установка сфейлена."
    exit 1
fi

# Делаем файл исполняемым
chmod +x "$SOURCE_FILE"

# Проверяем /usr/local/bin существует
if [ ! -d "/usr/local/bin" ]; then
    echo -e "Созаем дирректорию /usr/local/bin..."
    sudo mkdir -p /usr/local/bin
fi

# Создаём симлинк
echo -e "Создаем линк..."
sudo ln -sf "$SOURCE_FILE" "$TARGET_LINK"

# Проверяем успешность
if [ -L "$TARGET_LINK" ] && [ -e "$TARGET_LINK" ]; then
    echo -e "Установленно!"
    echo ""
    echo -e "   Запустите \"rfc -h\" для получения помощи =)."
else
    echo -e "Упс... Установка сфейлена."
    exit 1
fi

