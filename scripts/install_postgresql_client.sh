#########################################################################
# POSTGRES CLIENT INSTALLATION
#
# https://www.postgresql.org/download/linux/debian/
# Note apt-key is considered unsecure and signed-by used as a replacement
#########################################################################

CPU="$(dpkg --print-architecture)"
DISTR="$(awk -F= '/^ID=/{print $2}' /etc/os-release)"
DISTR_VERSION="$(awk -F= '/^VERSION_CODENAME=/{print $2}' /etc/os-release)"

echo "Installing postgresql-client-15"

mkdir -p /usr/share/keyrings/
if [ -f "/usr/share/keyrings/www.postgresql.org.gpg" ]
then
  echo "/usr/share/keyrings/www.postgresql.org.gpg exists"
else
  wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/www.postgresql.org.gpg
fi
if [ -f "/etc/apt/sources.list.d/pgdg.list" ]
then
  echo "/etc/apt/sources.list.d/pgdg.list exists"
else
  echo "deb [signed-by=/usr/share/keyrings/www.postgresql.org.gpg arch=$CPU] http://apt.postgresql.org/pub/repos/apt $DISTR_VERSION-pgdg main" > /etc/apt/sources.list.d/pgdg.list
fi
apt-get -y update && apt-get -y install postgresql-client-15
echo "postgresql-client-15 installed"