---
name: lan-own-ca
description: Give a LAN app HTTPS with its own CA (openssl + nginx in the app's CT), hand the CA out by a download link, and have each device trust it (Windows, Firefox, iPhone/iPad, Android, a Linux CT). Use when an app on the LAN needs HTTPS (e.g. for an MCP or OAuth sign-in), when a browser warns about its certificate, or on SSL_ERROR_RX_RECORD_TOO_LONG.
---

# Own CA for a LAN app

Built for Doska (#299), checked by its Jenkins job; the device steps weren't tried on real devices.

## Server (in the app's CT, Alpine, nginx in front)
```sh
apk add openssl
install -d -m 700 /etc/app-tls && cd /etc/app-tls
openssl req -x509 -newkey rsa:3072 -nodes -keyout ca.key -out ca.crt -days 3650 -subj "/CN=<App> <host> CA"
openssl req -newkey rsa:2048 -nodes -keyout server.key -out server.csr -subj "/CN=<ip>"
printf 'subjectAltName=IP:<ip>\nbasicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n' > ext.cnf
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 825 -extfile ext.cnf
chmod 600 ca.key server.key
install -m 644 ca.crt /var/lib/nginx/html/<app>-ca.crt
```
- `req -x509` gives the CA `CA:TRUE` (phones need it); the server certificate stays at 825 days (Apple's limit).
- The app's server block moves to `listen 8443 ssl;` with `ssl_certificate`/`ssl_certificate_key`; the plain port
  keeps one job besides redirecting, serving the CA:
  ```nginx
  server {
      listen 8080;
      location = /<app>-ca.crt { root /var/lib/nginx/html; }
      location / { return 301 https://<ip>:8443$request_uri; }
  }
  ```
  nginx's `mime.types` serves `.crt` as `application/x-x509-ca-cert`, which phones need to offer the install.
- Point the app's own public URL at `https://<ip>:8443` (OAuth and MCP metadata use it).
- Check: `curl -s -o got.crt -w '%{http_code} %{content_type}' http://<ip>:8080/<app>-ca.crt` → `200 application/x-x509-ca-cert`,
  then `curl --cacert got.crt https://<ip>:8443/` succeeds and `http://<ip>:8080/x` answers 301.

## The certificate is for one address
- An IP SAN covers only that IP. If the CT's address changes (DHCP gave .206 instead of .109, #312), the certificate
  and the redirect are wrong: pin the address first.
- A `.lan` name through the LAN proxy reaches 8080 and is redirected to `https://<ip>:8443`, so the address bar shows
  the IP. Keeping the name needs HTTPS on the proxy instead (Ahmad chose the IP, 2026-10-20).

## Devices (guide text opens with what it fixes)
"Your browser warns about `https://<ip>:8443` because <App> signed its own certificate. To stop the warning, put
`<app>-ca.crt` on each device that opens <App>."
- **Windows (Chrome, Edge):** open the link, open the file, Install Certificate… → Current User → Place all
  certificates in the following store → Browse… → Trusted Root Certification Authorities → Finish, Yes. Restart the browser.
- **Firefox:** Settings → Privacy & Security → Certificates → View Certificates… → Authorities → Import…, tick
  "Trust this CA to identify websites".
- **iPhone/iPad:** open the link in Safari, allow the download; Settings → General → VPN & Device Management → the
  profile → Install; then General → About → Certificate Trust Settings → turn it on.
- **Android:** open the link in Chrome; Settings → Security & privacy → More security & privacy → Encryption &
  credentials → Install a certificate → CA certificate (names vary by maker).
- **A Linux CT:** `ssh root@<pve-ip> pct exec <ctid> -- cat /etc/app-tls/ca.crt | tee /usr/local/share/ca-certificates/<app>.crt >/dev/null && update-ca-certificates`.
  Node programs (Claude Code) also need `NODE_EXTRA_CA_CERTS`: `mcp-lan-https` skill.

## Errors
- `SSL_ERROR_RX_RECORD_TOO_LONG` (Firefox) / `wrong version number` (curl): HTTPS sent to the plain port, e.g.
  `https://<ip>:8080`. Use `http://` there, or the 8443 address.
