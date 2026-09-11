#!/bin/bash

set -eux -o pipefail

if [[ -z $(git status --porcelain -- Containerfile) ]]; then
    echo "No changes made."
    exit 0
fi

git switch -c update-base-image
git commit -i Containerfile -m "Update base image"
git push "$(git remote | head -n 1)"

PR_URL="$(gh pr create --title 'Update base image' --body '' | tail -n 1)" || exit $?

gh pr merge --auto --squash "$PR_URL"
