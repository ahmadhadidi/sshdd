# Run Tests
``` bash
# Run all Remote
pytest tests/*_remote_*.py

# Run all Local
pytest tests/*_local_*.py

# Run all Config
pytest tests/*_config_*.py
```

# The "Total" Run
> To run everything in order and get a full report:
``` bash
pytest tests/ -v
```

# In parallel
> pytest-xdist (`python3 -m pip install pytest-xdist`) runs the suite on every core: ~2.5 min instead of ~20 (#25).
> The pre-commit hook does this when xdist is installed. Each test gets its own `TMPDIR` (conftest), which sshdd
> honours, so the temp-file leak check doesn't see other workers' files.

``` bash
pytest tests/ -m "not lxc and not serial" -n auto --dist worksteal   # then, on a quiet machine:
pytest tests/ -m "serial and not lxc"
```
Tests marked `serial` measure timing (arrow-key latency) and only mean something without other load (#34).
`--dist worksteal` beat the default scheduling: 150-153 s vs 172 s (3 runs each, 12 cores). More workers than
cores (16) was no faster and failed a timing-sensitive test; 8 workers took 208 s. The LXC tests (`-m lxc`, ~135 s)
run one at a time: they share CT 213's `authorized_keys`, and OpenSSH penalises bursts of connections.

# Everything, fastest
> `make test-all` (scripts/test-all.sh): local tests in parallel while the LXC tests run on CT 213, then the
> timing tests. ~2 min 45 s, against ~5 min 20 s one stage after another (2026-10-24, 12 cores).

# Fail Fast
> If you're developing and want the tests to stop the moment one of them fails (so you can fix it immediately):

``` bash
pytest tests/ -x
```

# See the TUI during the test
> If a test fails and you want to see the actual "live" render of the TUI during the automated run, use the -s flag:
``` bash
pytest tests/01_remote_generate_and_install.py -s
```

Avoid running other tests while the pre-commit hook runs: the leak check is per test now (own `TMPDIR`), but
both runs compete for CPU and the timing-sensitive screen tests can time out.
