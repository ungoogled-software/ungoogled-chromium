#!/bin/bash
# This script is for tag automation.

tags=$(git describe --tags `git rev-list --tags --max-count=1`)

commit=$(git rev-parse HEAD)

# Create next tag.
CHROMIUM_VERSION=$(cat chromium_version.txt)
UNGOOGLED_REVISION=$(cat revision.txt)
UPDATED_TAG="${CHROMIUM_VERSION}-${UNGOOGLED_REVISION}"

# Post a new tag to repo through GitHub API
curl -s -X POST https://api.github.com/repos/$REPO_OWNER/ungoogled-chromium/git/refs \
-H "Authorization: token $GITHUB_TOKEN" \
-d @- << EOF

{
  "ref": "refs/tags/$UPDATED_TAG",
  "sha": "$commit"
}
EOF
