# /pr

1. `git diff --staged` and `git diff` — review all changes
2. Write commit message following conventional commits (feat:, fix:, chore:, docs:)
3. `git add -A && git commit -m "message"`
4. `git push origin HEAD`
5. `gh pr create --title "[auto] message" --body "Description\n\nCloses #N"`
6. Return PR URL
