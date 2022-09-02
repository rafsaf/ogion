#!/bin/bash

# https://www.postgresql.org/download/linux/debian/
sudo apt update && apt install wget gnupg2

sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

sudo apt update && apt install postgresql-client-14