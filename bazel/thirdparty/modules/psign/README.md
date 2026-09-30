# psign

Authenticode signing on Linux (PE, MSI, PowerShell) via Azure Artifact Signing.
Built from source because we carry a patch:

- `0001-artifact-signing-correlation-id-for-scripts.patch`: forward the
  Artifact Signing correlation ID (`x-correlation-id`) when signing
  PowerShell scripts. Upstream 0.7.0 rejects the option for scripts; PE, CAB
  and MSI already send it. Drop the patch once upstream releases the fix.

## Regenerating `overlay/Cargo.Bazel.lock`

crate_universe cannot repin in a non-root module, so the lockfile is
generated with psign as the root module and shipped in the overlay:

```sh
M=bazel/thirdparty/modules/psign/<version>
mkdir gen && curl -sfL <source.json url> | tar xz -C gen --strip-components=1
cd gen
patch -p1 < "$OLDPWD/$M/patches/0001-artifact-signing-correlation-id-for-scripts.patch"
cp -rL "$OLDPWD/$M/overlay/." .  # -L: overlay/MODULE.bazel is a symlink
cp "$OLDPWD/.bazelversion" .
echo 'common --registry=https://bcr.bazel.build' > .bazelrc
CARGO_BAZEL_REPIN=1 bazel build //:psign-tool
cp Cargo.Bazel.lock "$OLDPWD/$M/overlay/"
```

Afterwards update the integrity hashes of the changed files in `source.json`.

On 2.5.0 (rules_rust 0.70.0), also add the root's
`rust.toolchain(versions = ["1.90.0"])` to the generated `MODULE.bazel`. This
rules_rust keys the lockfile digest by the manifest labels, which differ
between the standalone root (`//:Cargo.toml`) and check_mk
(`@@psign+//:Cargo.toml`). So afterwards set `"checksum"` in
`Cargo.Bazel.lock` to the "Expected Digest" a check_mk build reports, then
rehash it. Run `bazel shutdown` first; the server caches registry files.
