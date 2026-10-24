.PHONY: check update-docs test-all

check:          ## Syntax-check all lib/bash/*.sh and lib/ps/*.ps1 files
	@bash scripts/check.sh

test-all:       ## Every test, fastest order: local in parallel + LXC (CT 213) alongside, then timing tests
	@bash scripts/test-all.sh

update-docs:    ## Refresh function line numbers and ~NNN counts in CLAUDE.md
	@bash scripts/update-line-numbers.sh
