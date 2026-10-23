# Signing packages with `sign_package`

`sign_package` (`bazel/rules/sign_package.bzl`) signs an `.rpm` built by
Bazel (e.g. `//omd:rpm`) with a GPG key that lives only on the local
filesystem - never inside the Bazel workspace, output tree, runfiles, or
cache.

## Where the key lives

The private key is a plain GPG key file (armored or binary) somewhere
outside the repo, e.g. `$HOME/.keys/package-signing.key`. **Never commit a
private signing key.** Only the corresponding public key belongs in the
repo (see `docker_image/Check_MK-pubkey.gpg`).

## How to sign locally

```bash
bazel build \
    --//bazel/rules:signing_key_file=$HOME/.keys/package-signing.key \
    --//bazel/rules:signing_key_passphrase_file=$HOME/.keys/package-signing.passphrase \
    //omd:rpm_signed
```

The passphrase flag is only needed if the key is passphrase-protected, and
takes the _path to a file containing the passphrase_, never the passphrase
itself. Both flags are plain Bazel build settings, not `--action_env`, so
only targets that actually depend on them are affected when a value
changes. A relative key or passphrase path fails at analysis time, before
anything runs, with the exact flag to pass.

The signed output appears at `bazel-bin/omd/signed/<package name>`.

## Key identification

`sign_package`'s `expected_fingerprint` attribute pins the full 40-character
GPG fingerprint of `docker_image/Check_MK-pubkey.gpg`'s primary key (the
current release-signing key) and always signs with that exact key,
regardless of what else a key file contains. Not secret, safe to hardcode.

## Why this is deliberately non-hermetic

The private key can't be committed, so this action deliberately breaks
hermeticity to read it straight off the host filesystem. It:

- reads the key and passphrase-file paths from build settings instead of
  taking them as Bazel inputs, so neither file's contents is ever staged
  into the sandbox, output tree, or any cache - and, unlike
  `--action_env`, only targets that actually depend on the flags are
  affected when a value changes;
- runs with `execution_requirements = {"local": "1", "no-cache": "1"}` (
  `"local"` alone already implies unsandboxed, non-remote execution), so it
  never runs remotely or from a remote or disk cache, and can reach paths
  outside the workspace;
- gets a filtered `env` built from `ctx.configuration.default_shell_env`
  instead of `use_default_shell_env = True`, so the action only ever sees
  `PATH` - the key and passphrase paths reach it as plain arguments, not
  through the environment at all.

This action stays non-hermetic in isolation; whether that reaches the rest
of the build depends on what a caller wires a signed output into. A caller
that makes a signed output a default dependency means ordinary builds of
that dependency need `--//bazel/rules:signing_key_file` too.

Note that `no-cache` only disables the disk and remote action cache -
Bazel's own in-memory Skyframe/action cache still applies. Because the key
and passphrase-file paths are read from build settings rather than
declared as inputs, replacing the file at an unchanged path (e.g.
`~/.keys/package-signing.key`) is not a change Bazel can observe, so a
`bazel build` in the same server instance may reuse a previously-signed
output instead of re-signing. If you need a guaranteed re-sign on every
invocation, prefer running the signer as a `bazel run` command rather than
relying on this being a build action.

## Failure handling

Without `--//bazel/rules:signing_key_file`, every `sign_package` target is
incompatible rather than buildable, so building it without the flag fails
with Bazel's own incompatible-target error, and whole-repo target sweeps
(`//...`, `bazel query`/`cquery`) skip it entirely. Once the flag is set,
a relative key or passphrase path still fails analysis immediately, naming
the offending flag.

The signer itself fails before touching anything if:

- the key file doesn't exist (`Signing key does not exist: <path>`);
- the passphrase file is set but doesn't exist;
- the imported key's fingerprint doesn't match `expected_fingerprint`;
- `gpg`, `rpm`, or `rpmsign` (which `rpm --resign` execs as a separate
  process, and which EL splits into its own `rpm-sign` package) isn't
  installed.

It also verifies the result against the key it was just signed with, and
fails if that doesn't check out - catching a `--resign` that reported
success but signed nothing.

It never prints key or passphrase contents.

## CI

CI must pass only the key's and passphrase file's _paths_ via
`--//bazel/rules:signing_key_file`/`--//bazel/rules:signing_key_passphrase_file`,
the same way any other CI credential in this repo is bound to a path and
never echoed or committed.
