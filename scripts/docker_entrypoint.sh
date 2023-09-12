#!/bin/sh
echo "`date` start docker_entrypoint.sh..."
echo "`date` ROOT_MODE: $ROOT_MODE"

target_arch=$(arch | sed s/aarch64/arm64/ | sed s/x86_64/amd64/)
export BACKUPER_CPU_ARCHITECTURE=${target_arch}
echo "`date` detected cpu arch: '$target_arch'"

if [ "$ROOT_MODE" = "false" ] 
then
  echo "`date` will start backuper as user: '$SERVICE_NAME' without root privilages"
  set -e
  echo "`date` setting chown of directory '$FOLDER_PATH' and creating '$LOG_FOLDER_PATH'"
  chown -R ${SERVICE_NAME}:${SERVICE_NAME} ${FOLDER_PATH}
  mkdir -p ${LOG_FOLDER_PATH}
  chown -R ${SERVICE_NAME}:${SERVICE_NAME} ${LOG_FOLDER_PATH}
  
  echo "`date` finish docker_entrypoint.sh: run backuper as user '$SERVICE_NAME'"
  runuser -u ${SERVICE_NAME} -- $@
else
  echo "`date` finish docker_entrypoint.sh: run backuper as user: 'root'"
  $@
fi