#!/bin/sh
DB_COMPOSE_FILE="docker/docker-compose.dbs.yml"

git config user.name "GitHub Actions Bot"
git config user.email "<>"
git status
DIFF=$(git diff origin/main $DB_COMPOSE_FILE)
if [ "$DIFF" = "" ]
then
    echo "no changes detected"
else
    echo "file changed"
    git checkout -b main
    git add .
    git commit -m 'GitHub Actions Bot: updated docker-compose.dbs.yml'
    git push -u origin main
fi