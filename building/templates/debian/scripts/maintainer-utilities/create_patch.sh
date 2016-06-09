#!/bin/bash

TEXT_EDITOR_CMD=nano
DIFF_CMD="git diff --no-index"
FILE_PATH=$1

if [[ -z "${FILE_PATH}" ]]; then
    echo "Usage: $0 <FILE_TO_PATCH>"
    exit
fi

if [[ ! -f ${FILE_PATH} ]]; then
    echo "File does not exist."
    exit
fi

cp ${FILE_PATH} ${FILE_PATH}.orig
${TEXT_EDITOR_CMD} ${FILE_PATH}
read -p "Press [Enter] to continue:"
${DIFF_CMD} ${FILE_PATH}.orig ${FILE_PATH} | tail --lines=+3 | sed "s|${FILE_PATH}.orig|${FILE_PATH}|g" | ${TEXT_EDITOR_CMD} -
mv ${FILE_PATH}.orig ${FILE_PATH}
