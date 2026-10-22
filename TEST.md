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
pytest tests/ -m "not lxc" -n auto
```

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
