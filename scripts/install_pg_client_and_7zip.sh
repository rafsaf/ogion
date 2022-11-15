#!/bin/bash
set -e

apt-get -y update && apt-get install -y wget lsb-release gpg xz-utils
CPU="$(dpkg --print-architecture)"
DISTR="$(lsb_release -cs)"

#########################################################################
# POSTGRES CLIENT INSTALLATION
#
# https://www.postgresql.org/download/linux/debian/
# Note apt-key is considered unsecure and signed-by used as a replacement
#########################################################################

echo "Installing postgresql-client-15"
mkdir -p /usr/share/keyrings/
wget -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/www.postgresql.org.gpg
echo "deb [signed-by=/usr/share/keyrings/www.postgresql.org.gpg arch=$CPU] http://apt.postgresql.org/pub/repos/apt $DISTR-pgdg main" > /etc/apt/sources.list.d/pgdg.list
apt-get -y update && apt-get -y install postgresql-client-15
echo "postgresql-client-15 installed"

#########################################################################
# 7ZIP INSTALLATION
#
# https://www.7-zip.org/download.html
#########################################################################

ZIP_DIR="/opt/7zip"
ZIP_TAR_FILE="$ZIP_DIR/7zip.tar.xz"

if [ "$CPU" = "amd64" ]
then
  echo "Installing 7zip for amd64"
  ZIP_DOWNLOAD_URL="https://www.7-zip.org/a/7z2201-linux-x64.tar.xz"
elif [ "$CPU" = "arm64" ]
then
  echo "Installing 7zip for arm64"
  ZIP_DOWNLOAD_URL="https://www.7-zip.org/a/7z2201-linux-arm64.tar.xz"
else
  echo "Unknown cpu architecture $CPU: expected amd64 or arm64"
  exit 1
fi

mkdir -p $ZIP_DIR
wget --quiet -O $ZIP_TAR_FILE $ZIP_DOWNLOAD_URL
cd $ZIP_DIR
ls
tar -xf $ZIP_TAR_FILE
rm -f $ZIP_TAR_FILE
echo "7zip installed: /opt/7zip/7zz"
 