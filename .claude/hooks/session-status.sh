#!/bin/sh
# SessionStart hook: open TODO items and the branch state, so a session starts knowing where things stand.
# Register in .claude/settings.json (setup/INIT.md, Phase 4 step 10). Never fails the session.
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
todo="$HOME/.claude/skills/todo-tables/scripts/todo.py"
if [ -e .claude/TODO.md ] && [ -f "$todo" ]; then
    for s in progress review inbox; do
        echo "### TODO $s"
        python3 "$todo" list "$s" 15 2>/dev/null
    done
fi
if git rev-parse --git-dir >/dev/null 2>&1; then
    echo "### Branch"
    git status -sb 2>/dev/null | head -1
    printf 'uncommitted files: %s\n' "$(git status --porcelain 2>/dev/null | wc -l)"
fi
exit 0
