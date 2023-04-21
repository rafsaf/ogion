#!/bin/bash
set -e

chown -R ${SERVICE_NAME}:${SERVICE_NAME} ${FOLDER_PATH}
runuser -u ${SERVICE_NAME} -- $@