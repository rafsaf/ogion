#!/bin/sh
# To be run in github action update_compose_dbs.yml

git config user.name "GitHub Actions Bot"
git config user.email "<>"
git status
DIFF=$(git diff origin/main)
if [ "$DIFF" = "" ]
then
    echo "no changes detected"
else
    echo "file changed"
    make tests_amd64
    echo "merge changes"
    timestamp=$(date +%s)
    branch="update-docker-compose-dbs-$timestamp"
    git checkout -b $branch
    git add .
    git commit -m 'GitHub Actions Bot: updated docker-compose.dbs.yml file'
    git push -u origin $branch
    gh pr create -B main -H $branch --title 'update docker-compose.dbs.yml file' --body 'Created by Github action'
    gh pr merge $branch --merge --admin --delete-branch
fi