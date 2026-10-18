---
name: ct-connection-closed
description: Use when CT 213 (or any OpenSSH 9.8+ host) LXC tests fail with "Connection closed by 192.168.0.213 port 22" before any password prompt, or a host-key scan comes back empty for a host that is up.
---

# "Connection closed" from CT 213 before authentication

**Symptom:** `-m lxc` tests fail at the very first prompt with `Connection closed by 192.168.0.213 port 22`, or
sshdd's host-key check finds nothing to compare. A run a few minutes later passes.

**Likely cause:** OpenSSH 9.8+ `PerSourcePenalties` (on by default; CT 213 runs 10.3). Each failed login adds
5 s of penalty (`authfail`), and each connection that never logs in adds 1 s (`noauth`, e.g. `ssh-keyscan`, one
connection per key type). At 15 s the source IP is refused for a while. `test_wrong_password_message` adds
authfail penalties on purpose. Not proven from sshd's log: that needs root on the CT.

**Check:** `ssh -i ~/.ssh/dev-lan -o BatchMode=yes kraid@192.168.0.213 true` works (key logins add no
penalty), while a password login is closed straight away. Wait about a minute and re-run.

**Rules that came from it:**
- sshdd scans one key type only (`_hostkey_check`), so a check costs 1 s of penalty, not 3.
- Tests that fail logins on purpose run late in the LXC order; don't add more of them without need.
