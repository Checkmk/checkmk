echo -e "\n###############################################################################"

BRANCH=$(git branch | grep \* | cut -d ' ' -f2)
echo "Current branch: $BRANCH"

echo "Pulling the latest changes from the remote repository..."
git pull --no-rebase origin "$BRANCH"

echo "Committing all changes to the local repository..."
git add .
git commit -m "wippy wip, mobby wip"

echo "Pushing all changes to the remote repository..."
git push origin "$BRANCH"

echo "Done for now!"
