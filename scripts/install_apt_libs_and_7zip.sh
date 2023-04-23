#!/bin/bash
set -e

apt-get -y update && apt-get install -y wget lsb-release gpg xz-utils
CPU="$(dpkg --print-architecture)"
DISTR="$(lsb_release -cs)"
SCRIPT_PATH=`readlink -f "$0"`
SCRIPT_DIR=`dirname "$SCRIPT_PATH"`

#########################################################################
# POSTGRES CLIENT INSTALLATION
#
# https://www.postgresql.org/download/linux/debian/
# Note apt-key is considered unsecure and signed-by used as a replacement
#########################################################################

echo "Installing postgresql-client-15"
mkdir -p /usr/share/keyrings/
if [ -f "/usr/share/keyrings/www.postgresql.org.gpg" ]
then
  echo "/usr/share/keyrings/www.postgresql.org.gpg exists"
else
  cat $SCRIPT_DIR/keys/www.postgresql.org.asc | gpg --dearmor -o /usr/share/keyrings/www.postgresql.org.gpg
fi
if [ -f "/etc/apt/sources.list.d/pgdg.list" ]
then
  echo "/etc/apt/sources.list.d/pgdg.list exists"
else
  echo "deb [signed-by=/usr/share/keyrings/www.postgresql.org.gpg arch=$CPU] http://apt.postgresql.org/pub/repos/apt $DISTR-pgdg main" > /etc/apt/sources.list.d/pgdg.list
fi
apt-get -y update && apt-get -y install postgresql-client-15
echo "postgresql-client-15 installed"

#########################################################################
# MYSQL CLIENT INSTALLATION
#
# https://dev.mysql.com/doc/mysql-apt-repo-quick-guide/en/
#########################################################################

echo "Installing mysql-client"
mkdir -p /usr/share/keyrings/
if [ -f "/usr/share/keyrings/pgp.mit.edu.gpg" ]
then
  echo "/usr/share/keyrings/pgp.mit.edu.gpg exists"
else
  cat $SCRIPT_DIR/keys/pgp.mit.edu.asc | gpg --dearmor -o /usr/share/keyrings/pgp.mit.edu.gpg
fi
if [ -f "/etc/apt/sources.list.d/mysql.list" ]
then
  echo "/etc/apt/sources.list.d/mysql.list exists"
else
  echo "deb [signed-by=/usr/share/keyrings/pgp.mit.edu.gpg arch=$CPU] http://repo.mysql.com/apt/debian/ $DISTR mysql-8.0" > /etc/apt/sources.list.d/mysql.list
fi
apt-get -y update && apt-get -y install mysql-client
echo "mysql-client installed"

#########################################################################
# 7ZIP INSTALLATION
#
# https://www.7-zip.org/download.html
#########################################################################

AMD64_DIR="$SCRIPT_DIR/../bin/7zip/amd64"
AMD64_7ZZ="$AMD64_DIR/7zz"

ARM64_DIR="$SCRIPT_DIR/../bin/7zip/arm64"
ARM64_7ZZ="$ARM64_DIR/7zz"

if [ -f "$AMD64_7ZZ" ]
then
  echo "$AMD64_7ZZ exists"
else
  mkdir -p $AMD64_DIR
  cd $AMD64_DIR
  wget --quiet "https://www.7-zip.org/a/7z2201-linux-x64.tar.xz"
  tar -xf "7z2201-linux-x64.tar.xz"
  rm -f "7z2201-linux-x64.tar.xz"
fi

if [ -f "$ARM64_7ZZ" ]
then
  echo "$ARM64_7ZZ exists"
else
  mkdir -p $ARM64_DIR
  cd $ARM64_DIR
  wget --quiet "https://www.7-zip.org/a/7z2201-linux-arm64.tar.xz"
  tar -xf "7z2201-linux-arm64.tar.xz"
  rm -f "7z2201-linux-arm64.tar.xz"
fi


if [ "$CPU" = "amd64" ]
then
  cp $AMD64_7ZZ "$SCRIPT_DIR/../bin/7zz"
elif [ "$CPU" = "arm64" ]
then
  cp $ARM64_7ZZ "$SCRIPT_DIR/../bin/7zz"
else
  echo "Unknown cpu architecture $CPU: expected amd64 or arm64"
  exit 1
fi