import pytest

pytestmark = pytest.mark.lxc

ESC   = "\x1b"
ENTER = "\r"


def test_remote_test_connection(run_tui, isolated_home):
    # The host list needs a configured host (temp HOME starts empty, T0).
    (isolated_home / ".ssh" / "config").write_text("Host sshdd-test\n    HostName 192.168.0.213\n    User testuser\n")
    child = run_tui("--user testuser")
    child.send("T")
    child.expect("Test SSH Connection")
    child.expect("Select remote host")
    child.send(ESC)
    child.send("q")
