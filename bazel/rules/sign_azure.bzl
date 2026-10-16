"""Authenticode-signs the files of a tar via Azure Artifact Signing, as a build
action. Modelled on //bazel/rules:sign_package.bzl, see sign_package.md.

The Azure settings, including the client secret, live in a file on the host
whose absolute path is given by
`--//bazel/rules:azure_signing_credentials_file`, e.g.:

    bazel build \\
        --//bazel/rules:azure_signing_credentials_file=$HOME/.keys/azure-signing.env \\
        //agents/wnx:check_mk_agent_msi

The file holds one KEY=VALUE line per AZURE_ARTIFACT_SIGNING_* setting (see
azure_signing.sh). Only its path reaches Bazel: the file is never declared as a
Bazel input, and the action reads it directly off the host filesystem, so it
runs locally and uncached. Without the flag, a sign_tar_azure target is
`target_compatible_with`-incompatible rather than buildable.
"""

load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

_RELATIVE_PATH = """
Azure signing credentials file path for {label} is not absolute: {path}

Bazel actions do not run in your working directory, so this path must be
absolute.
"""

def _sign_tar_azure_impl(ctx):
    credentials_file = ctx.attr._credentials_file[BuildSettingInfo].value
    if not credentials_file.startswith("/"):
        fail(_RELATIVE_PATH.format(label = ctx.label, path = credentials_file))
    out = ctx.actions.declare_file(ctx.label.name + ".tar")

    args = ctx.actions.args()
    args.add(ctx.file._lib)
    args.add(ctx.executable._psign)
    args.add(ctx.executable._osslsigncode)
    args.add(credentials_file)
    args.add(ctx.file.src)
    args.add(out)
    args.add_all(ctx.files._roots)

    # Forward only PATH, as sign_package does: the credentials reach the action
    # through the file, not through the environment.
    shell_env = ctx.configuration.default_shell_env
    env = {"PATH": shell_env["PATH"]} if "PATH" in shell_env else {}

    ctx.actions.run(
        executable = ctx.attr._signer[DefaultInfo].files_to_run,
        arguments = [args],
        inputs = [ctx.file.src, ctx.file._lib] + ctx.files._roots,
        tools = [
            ctx.attr._psign[DefaultInfo].files_to_run,
            ctx.attr._osslsigncode[DefaultInfo].files_to_run,
        ],
        outputs = [out],
        mnemonic = "SignAzure",
        progress_message = "Signing the files of %{input} via Azure Artifact Signing",
        use_default_shell_env = False,
        env = env,
        execution_requirements = {
            # "local" alone already implies unsandboxed, non-remote.
            "local": "1",
            "no-cache": "1",
        },
    )
    return [DefaultInfo(files = depset([out]))]

_sign_tar_azure = rule(
    implementation = _sign_tar_azure_impl,
    doc = """Signs every file of the flat tar `src` and packs the signed files
into <name>.tar, with the same layout.""",
    attrs = {
        "src": attr.label(allow_single_file = [".tar"], mandatory = True),
        "_credentials_file": attr.label(
            default = "//bazel/rules:azure_signing_credentials_file",
        ),
        "_lib": attr.label(
            default = "//bazel/rules:azure_signing",
            allow_single_file = True,
        ),
        "_osslsigncode": attr.label(
            default = "@osslsigncode",
            executable = True,
            cfg = "exec",
        ),
        "_psign": attr.label(
            default = "@psign",
            executable = True,
            cfg = "exec",
        ),
        "_roots": attr.label(default = "//tests/packaging:signing_roots"),
        "_signer": attr.label(
            default = "//bazel/rules:sign_tar_azure",
            executable = True,
            cfg = "exec",
        ),
    },
)

def sign_tar_azure(name, target_compatible_with = [], **kwargs):
    """`_sign_tar_azure`, marked incompatible without signing credentials."""
    _sign_tar_azure(
        name = name,
        target_compatible_with = select({
            "//bazel/rules:azure_signing_credentials_file_unset": ["@platforms//:incompatible"],
            "//conditions:default": [],
        }) + target_compatible_with,
        **kwargs
    )
