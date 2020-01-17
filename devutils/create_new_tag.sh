#!/bin/bash
# This script is for tag automation.

tags=$(git describe --tags `git rev-list --tags --max-count=1`)

commit=$(git rev-parse HEAD)

# Create next tag.
UPDATED_TAG='%s-%s' $(cat chromium_version.txt) $(cat revision.txt)

# Do not push new tag if "UPDATED_TAG" already exists.
if [ $UPDATED_TAG == $tags ]
then
    return
fi

# Post a new tag to repo through GitHub API
git_refs_url=$(jq .repository.git_refs_url $GITHUB_EVENT_PATH | tr -d '"' | sed 's/{\/sha}//g')
curl -s -X POST $git_refs_url \
-H "Authorization: token $GITHUB_TOKEN" \
-d @- << EOF

{
  "ref": "refs/tags/$UPDATED_TAG",
  "sha": "$commit"
}
EOF
