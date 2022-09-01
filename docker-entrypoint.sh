#!/bin/bash

chown -R ${SERVICE_NAME}:${SERVICE_NAME} ${PGDUMP_FOLDER_PATH} ${PGDUMP_LOG_FOLDER_PATH}
exec runuser -u ${SERVICE_NAME} "$@"