"""Signs an .rpm package locally with a GPG key that lives only on the host
filesystem - never as a Bazel input. See sign_package.md.
"""

load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

# Fingerprint of docker_image/Check_MK-pubkey.gpg's primary (release-signing)
# key. Not secret, safe to hardcode - shared so every sign_package caller
# checks against the same key.
RELEASE_KEY_FINGERPRINT = "B1E7106575B723F00611C612434DAC48C4503261"

_RELATIVE_PATH = """
{what} path for {label} is not absolute: {path}

Bazel actions do not run in your working directory, so this path must be
absolute.
"""

def _host_path(label, value, what):
    if not value:
        return ""
    if not value.startswith("/"):
        fail(_RELATIVE_PATH.format(what = what, label = label, path = value))
    return value

def _sign_package_impl(ctx):
    src = ctx.file.src
    out = ctx.actions.declare_file(ctx.attr.out or ("signed/" + src.basename))

    key_file = _host_path(
        ctx.label,
        ctx.attr._key_file[BuildSettingInfo].value,
        "Key file",
    )
    passphrase_file = _host_path(
        ctx.label,
        ctx.attr._passphrase_file[BuildSettingInfo].value,
        "Passphrase file",
    )

    args = ctx.actions.args()
    args.add(src)
    args.add(out)
    args.add(key_file)
    args.add(passphrase_file)
    args.add(ctx.attr.expected_fingerprint)

    # Forward only PATH, not the full --action_env-populated default shell
    # env, so this unsandboxed action can't see more than intended. The key
    # and passphrase paths reach the action as plain arguments above, not
    # through the environment.
    shell_env = ctx.configuration.default_shell_env
    env = {"PATH": shell_env["PATH"]} if "PATH" in shell_env else {}

    ctx.actions.run(
        executable = ctx.executable._signer,
        arguments = [args],
        inputs = [src],
        outputs = [out],
        mnemonic = "SignPackage",
        progress_message = "Signing %{input}",
        use_default_shell_env = False,
        env = env,
        execution_requirements = {
            # "local" alone already implies unsandboxed, non-remote.
            "local": "1",
            "no-cache": "1",
        },
    )
    return [DefaultInfo(files = depset([out]))]

_sign_package = rule(
    implementation = _sign_package_impl,
    doc = """Signs `src` (an .rpm built by e.g. pkg_rpm_from_tar) and produces
a signed copy under signed/<src's basename> (or `out`, if set).

Reads the private key from the absolute host path given by
`--//bazel/rules:signing_key_file` and, if set, a *path to a file holding
the passphrase* from `--//bazel/rules:signing_key_passphrase_file`, e.g.:

    bazel build \\
        --//bazel/rules:signing_key_file=$HOME/.keys/package-signing.key \\
        --//bazel/rules:signing_key_passphrase_file=$HOME/.keys/package-signing.passphrase \\
        //omd:rpm_signed

Only paths ever reach Bazel this way - never the passphrase's contents. Both
flags are read once and shared by every sign_package target in the build.
Without `--//bazel/rules:signing_key_file`, a sign_package target is
`target_compatible_with`-incompatible rather than buildable (see
sign_package.md); once the flag is set, a relative path still fails
analysis immediately, naming the offending flag.

Neither the key file nor the passphrase file is ever declared as a Bazel
input, output, or tool: both are read directly off the host filesystem by
the action's shell script, which runs locally and uncached so it can reach
them (see sign_package.md for why "always runs" isn't quite true).

`expected_fingerprint` must be the full 40-character GPG fingerprint of the
signing key (not secret - safe to hardcode). The signer looks up that exact
fingerprint among the imported secret keys and signs with it specifically,
so a key file that doesn't contain the intended key (e.g. only a wrong one)
fails loudly instead of silently signing with something else. Any other,
unrelated key in the same file changes nothing - only the matched
fingerprint is ever used.
""",
    attrs = {
        "expected_fingerprint": attr.string(
            mandatory = True,
            doc = "Full 40-character GPG fingerprint the imported signing " +
                  "key must match. Not secret.",
        ),
        "out": attr.string(
            doc = "Output file name; defaults to src's own basename.",
        ),
        "src": attr.label(allow_single_file = True, mandatory = True),
        "_key_file": attr.label(default = "//bazel/rules:signing_key_file"),
        "_passphrase_file": attr.label(default = "//bazel/rules:signing_key_passphrase_file"),
        "_signer": attr.label(
            default = "//bazel/rules:sign_package.sh",
            allow_single_file = True,
            executable = True,
            cfg = "exec",
        ),
    },
)

def sign_package(name, target_compatible_with = [], **kwargs):
    """`_sign_package`, marked incompatible when no signing key is configured.

    Keeps whole-repo target sweeps (e.g. `bazel query`/`cquery`) from
    tripping over an unconfigured key. See sign_package.md.
    """
    _sign_package(
        name = name,
        target_compatible_with = select({
            "//bazel/rules:signing_key_file_unset": ["@platforms//:incompatible"],
            "//conditions:default": [],
        }) + target_compatible_with,
        **kwargs
    )
