#!/bin/bash
#########################################################################
# MARIADB CLIENT INSTALLATION
#
# https://mariadb.com/kb/en/mariadb-package-repository-setup-and-usage/
#########################################################################
echo "Installing mariadb-client with ready script"
curl -LsS https://r.mariadb.com/downloads/mariadb_repo_setup | bash
apt-get -y update && apt-get -y install mariadb-client
echo "mariadb-client installed"