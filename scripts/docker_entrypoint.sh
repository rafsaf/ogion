#!/bin/bash

chown -R ${PD_SERVICE_NAME}:${PD_SERVICE_NAME} ${PD_FOLDER_PATH} ${PD_LOG_FOLDER_PATH}
exec runuser -u ${PD_SERVICE_NAME} "$@"