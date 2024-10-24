#!/bin/bash
#########################################################################
# POSTGRES CLIENT INSTALLATION
#
# https://www.postgresql.org/download/linux/debian/
# Note apt-key is considered unsecure and signed-by used as a replacement
#########################################################################
CPU="$(dpkg --print-architecture)"
DISTR_VERSION="$(awk -F= '/^VERSION_CODENAME=/{print $2}' /etc/os-release)"

echo "Installing postgresql-client-17"

mkdir -p /etc/apt/keyrings/
if [ -f "/etc/apt/keyrings/www.postgresql.org.gpg" ]
then
  echo "/etc/apt/keyrings/www.postgresql.org.gpg exists"
else
  wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/keyrings/www.postgresql.org.gpg
fi
if [ -f "/etc/apt/sources.list.d/pgdg.list" ]
then
  echo "/etc/apt/sources.list.d/pgdg.list exists"
else
  echo "deb [signed-by=/etc/apt/keyrings/www.postgresql.org.gpg arch=$CPU] http://apt.postgresql.org/pub/repos/apt $DISTR_VERSION-pgdg main" > /etc/apt/sources.list.d/pgdg.list
fi
apt-get -y update && apt-get -y install postgresql-client-17
echo "postgresql-client-17 installed"