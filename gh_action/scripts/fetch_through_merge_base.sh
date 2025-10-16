#!/bin/sh

# Fetch through merge-base script
# Based on rmacklin/fetch-through-merge-base action

DEEPEN_LENGTH=${DEEPEN_LENGTH:-10}

echo "Fetching commits through merge-base..."
echo "Base ref: $BASE_REF"
echo "Head ref: $HEAD_REF"
echo "Deepen length: $DEEPEN_LENGTH"

# Fetch the base ref first
git fetch --progress --depth=1 origin "+refs/heads/$BASE_REF:refs/heads/$BASE_REF"

# Keep deepening until we find the merge-base
while [ -z "$( git merge-base "$BASE_REF" "$HEAD_REF" )" ]; do
  echo "Deepening history by $DEEPEN_LENGTH commits..."
  git fetch -q --deepen="$DEEPEN_LENGTH" origin "$BASE_REF" "$HEAD_REF";
done

echo "Merge-base found: $(git merge-base "$BASE_REF" "$HEAD_REF")"
echo "Fetch through merge-base completed successfully!"
