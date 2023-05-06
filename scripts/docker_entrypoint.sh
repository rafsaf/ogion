#!/bin/bash
echo "start backuper as user $SERVICE_NAME"
set -e
echo "setting chown of directory $FOLDER_PATH"
chown -R ${SERVICE_NAME}:${SERVICE_NAME} ${FOLDER_PATH}
echo "running backuper using runuser"
runuser -u ${SERVICE_NAME} -- $@