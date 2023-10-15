#!/bin/sh
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
DB_COMPOSE_FILE="$SCRIPT_DIR/../docker/docker-compose.dbs.yml"

cd $SCRIPT_DIR/../
make update_compose_db_file
DIFF=$(git diff $DB_COMPOSE_FILE)
if [ "$DIFF" = "" ]
then
    echo "no changes detected"
else
    echo "file changed"
    timestamp=$(date +%s)
    branch="update-docker-compose-dbs-$timestamp"
    msg="update docker-compose.dbs.yml file"
    git branch $branch
    git commit -am $msg
    git push -u origin $branch
    gh pr create -B main -H $branch --title $msg --body 'Created by Github action'
fi