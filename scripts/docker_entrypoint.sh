#!/bin/bash
set -e

chown -R ${PD_SERVICE_NAME}:${PD_SERVICE_NAME} ${PD_FOLDER_PATH}
runuser -u ${PD_SERVICE_NAME} -- $@