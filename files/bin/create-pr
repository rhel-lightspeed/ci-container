#!/bin/bash

set -eux -o pipefail

if [[ -z $(git status --porcelain -- Containerfile) ]]; then
    echo "No changes made."
    exit 0
fi

git switch -c "update-base-image-$(date +%s)"
git commit -i Containerfile -m "Update base image"
git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
git push origin HEAD

PR_URL="$(gh pr create --title 'Update base image' --body '' | tail -n 1)" || exit $?
gh pr merge --auto --squash "$PR_URL"
