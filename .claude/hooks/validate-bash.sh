#!/bin/bash
# validate-bash.sh
# Pre-execution hook: blocks high-risk bash commands in the Aureus RM repo.
# Claude Code passes tool input via stdin as JSON: {"tool_input": {"command": "..."}}
# Add patterns to BLOCKED_PATTERNS to extend coverage.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

if [ -z "$COMMAND" ]; then
    exit 0
fi

BLOCKED_PATTERNS=(
  "rm -rf"
  "DROP TABLE"
  "DELETE FROM"
  "git push --force"
  "git reset --hard"
  "chmod 777"
  "curl.*\|.*bash"
  "wget.*\|.*sh"
)

for pattern in "${BLOCKED_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qiE "$pattern"; then
    echo "BLOCKED: command matches restricted pattern: $pattern" >&2
    echo "Command: $COMMAND" >&2
    exit 1
  fi
done

exit 0
