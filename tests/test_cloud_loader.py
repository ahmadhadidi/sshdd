"""
Regression test for TODO #12: a cloud run (bash <(curl ...) sshdd.sh) must load every lib
without errors. Serves this checkout over HTTP and points the loader's _BASE_URL at it.
"""
import functools
import http.server
import os
import subprocess
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_cloud_run_loads_libs_cleanly(tmp_path):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    srv.RequestHandlerClass.log_message = lambda *a: None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}"
        src = open(os.path.join(ROOT, "sshdd.sh")).read()
        src = src.replace('_BASE_URL="https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main"',
                          f'_BASE_URL="{url}"')
        assert url in src
        # Stop right after the loader: show_main_menu would need a TTY.
        src = src.replace("unset _lib _source_lib", "echo LOADED; type select_from_list >/dev/null && exit 0\nunset _lib _source_lib", 1)
        script = tmp_path / "sshdd.sh"   # no lib/bash beside it, like bash <(curl ...)
        script.write_text(src)
        r = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=30)
    finally:
        srv.shutdown()
    assert r.returncode == 0, r.stderr
    assert "LOADED" in r.stdout
    assert r.stderr == "", r.stderr
