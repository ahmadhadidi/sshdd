import subprocess
import time

import pexpect


def test_local_list_ssh_keys(run_tui, isolated_home):
    """L hotkey opens the key inventory; Q closes it and returns to main menu."""
    # The inventory needs a key (temp HOME starts empty, T0).
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(isolated_home / ".ssh" / "k1")], check=True)
    child = run_tui()
    child.send("L")
    child.expect("List SSH Keys", timeout=5)
    child.expect("Up/Dn navigate", timeout=5)
    time.sleep(0.2)
    child.send("Q")
    child.expect("SSHDD -- axc.sh", timeout=5)
    time.sleep(0.15)
    child.send("Q")
    child.expect(pexpect.EOF, timeout=5)
