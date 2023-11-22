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
    timestamp=$(date +%s)
    branch="update-docker-compose-dbs-$timestamp"
    git checkout -b $branch
    git add .
    git commit -m 'GitHub Actions Bot: updated docker-compose.dbs.yml file'
    git push -u origin $branch
    gh pr create -B main -H $branch --title 'update docker-compose.dbs.yml file' --body 'Created by Github action'
    gh pr merge $branch --merge
fi