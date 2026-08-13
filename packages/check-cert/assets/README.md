# Test assets

Certificates compiled into the tests with `include_bytes!`. Each one is picked
for a reason, so check the test before you replace one.

- `cert.der`, `root-ca.der` — a leaf and its issuing CA, the only valid chain
  here. **Must be valid at run time** because `tests/certificate.rs` and
  `tests/verify.rs` assert exit code 0. The content is otherwise unremarkable.
- `IGC_A.der` — fills every subject field and issuer field the checker reads.
  **Must stay expired** because `tests/igca_cert.rs` expects
  `Certificate expired (Oct 17 14:29:22 2020 +00:00)` verbatim.
- `ee-pss-sha1-cert.pem`, `ee-pss-sha256-cert.pem` — the only `rsassa-pss`
  coverage. Valid until 2117.
- `certificate.der` — parser input for `try_to_parse` in `src/truststore.rs`.
  The expiry date does not matter because nothing validates it.

The previous pair expired on 2026-08-12 and broke the two tests. The replacement
is valid until 2126. No private key is kept here, so regenerate both
certificates together and commit only the two `.der` files.

```sh
openssl req -x509 -newkey rsa:2048 -noenc -sha256 -days 36525 \
    -subj "/C=AU/ST=Some-State/O=Internet Widgits Pty Ltd" \
    -addext "basicConstraints=CA:TRUE" -keyout ca.key -out ca.pem
openssl req -new -newkey rsa:2048 -noenc -sha256 \
    -subj "/C=AU/ST=Some-State/O=Internet Widgits Pty Ltd/CN=foobar.com" \
    -keyout leaf.key -out leaf.csr
openssl x509 -req -in leaf.csr -CA ca.pem -CAkey ca.key -days 36525 -sha256 \
    -out leaf.pem
openssl x509 -in ca.pem -outform DER -out root-ca.der
openssl x509 -in leaf.pem -outform DER -out cert.der
```
