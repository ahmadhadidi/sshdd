#!/usr/bin/env bash
# scripts/test-all.sh — every test, fastest order (TODO #35, measured in TEST.md):
#   1. local tests in parallel (xdist, worksteal) while the LXC tests run one at a time on CT 213
#   2. the timing tests (-m serial) afterwards, on a quiet machine
# ~2 min 45 s on 12 cores, against ~5 min 20 s one stage after another. Exit 1 if any stage failed.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

par=(); python3 -c 'import xdist' 2>/dev/null && par=(-n auto --dist worksteal)
lxc_log=$(mktemp "${TMPDIR:-/tmp}/sshdd-lxc-tests.XXXXXX")
lxc_pid=''
trap '[[ -n $lxc_pid ]] && kill "$lxc_pid" 2>/dev/null; rm -f "$lxc_log"' EXIT
trap 'exit 130' INT TERM HUP   # run the EXIT trap on Ctrl+C too

# set -m: without job control a background job ignores SIGINT/SIGQUIT, and so would every ssh the tests
# start, so the Ctrl+C tests failed. Its own process group also keeps a Ctrl+C here from reaching it: the
# EXIT trap stops it instead.
set -m
python3 -m pytest tests/ -m lxc -q -rfE -p no:cacheprovider >"$lxc_log" 2>&1 &
lxc_pid=$!
set +m
printf '  Local tests (parallel), LXC tests on CT 213 alongside...\n'
python3 -m pytest tests/ -m "not lxc and not serial" -q -rfE "${par[@]}"; local_rc=$?
wait "$lxc_pid"; lxc_rc=$?; lxc_pid=

printf '\n  LXC tests (CT 213):\n'
if (( lxc_rc )); then cat "$lxc_log"; else tail -n 1 "$lxc_log"; fi

printf '\n  Timing tests (serial):\n'
python3 -m pytest tests/ -m "serial and not lxc" -q -rfE; serial_rc=$?

failed=''
(( local_rc ))  && failed+=' local'
(( lxc_rc ))    && failed+=' lxc'
(( serial_rc )) && failed+=' timing'
if [[ -n $failed ]]; then
    printf '\n  \e[31mFailed:%s\e[0m\n' "$failed"
    exit 1
fi
printf '\n  \e[32mAll tests passed.\e[0m\n'
