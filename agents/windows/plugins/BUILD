load("@rules_pkg//pkg:mappings.bzl", "pkg_files", "strip_prefix")
load("//bazel/rules:pkg.bzl", "pkg_tar")
load("//bazel/rules:sign_azure.bzl", "sign_tar_azure")

# Sign all PowerShell scripts in the current directory.
# `build bazel //agents/windows/plugins:all`
#
# We are using make variables, $, and $@ because we have no correct labels

filegroup(
    name = "plugins",
    srcs = glob(
        ["**"],
        exclude = [
            "BUILD",
            "reference/**",
            "scripts/**",
            ".signed/**",
            ".gitattributes",
            ".gitignore",
            "**/OWNERS",
            ".f12",
            "*.ps1",
        ],
    ),
    visibility = ["//visibility:public"],
)

filegroup(
    name = "signed_ps1",
    srcs = glob(
        [".signed/*.ps1"],
        allow_empty = True,
        # Signed along with the plugins for the MSI (see TO_SIGN_SCRIPTS), but not a plugin.
        exclude = [".signed/configure_and_exec.ps1"],
    ),
    visibility = ["//visibility:public"],
)

# The MSI's Product.wxs also needs the PowerShell plugins, which :plugins excludes.
filegroup(
    name = "msi_cmk_plugin_files",
    srcs = glob(["*.ps1"]),
    visibility = ["//agents/wnx:__pkg__"],
)

# Every PowerShell script embedded in the MSI (agents/wnx/install/Product.wxs takes
# them all from the signed folder), plus the ones the bakery ships.
# May contain local file target labels, or cross package labels
# from migrated bakery plugins under cmk/plugins/<family>/
# In the latter case, the file target must be exposed to this package.
TO_SIGN_SCRIPTS = [
    "arcserve_backup.ps1",
    "citrix_farm.ps1",
    "citrix_licenses.ps1",
    "citrix_xenapp.ps1",
    "hyperv_vms_guestinfos.ps1",
    "hyperv_vms.ps1",
    "iis_app_pool_state.ps1",
    "kaspersky_av_client.ps1",
    "mk_inventory.ps1",
    "mk_msoffice.ps1",
    "mk_mysql.ps1",
    "mk_oracle.ps1",
    "msexch_dag.ps1",
    "msexch_database.ps1",
    "nvidia_smi.ps1",
    "rds_licenses.ps1",
    "sansymphony.ps1",
    "veeam_backup_status.ps1",
    "win_printers.ps1",
    "windows_if.ps1",
    "windows_multipath.ps1",
    "windows_os_bonding.ps1",
    "windows_tasks.ps1",
    "windows_updates.ps1",
    "hyperv_host.ps1",
    # Not a plugin: the agent runs every PowerShell plugin through it.
    "//agents/wnx:install/resources/configure_and_exec.ps1",
]

# Signed copies are flat, keyed by basename: cross-package labels may carry a
# path below their package (e.g. agents/veeam_backup_status.ps1).
SIGNED_NAMES = {n: n.split(":")[-1].split("/")[-1] for n in TO_SIGN_SCRIPTS}

[
    genrule(
        name = "sign_" + name,
        srcs = [n],
        outs = ["signed/" + name],
        cmd_bat = "$(execpath scripts/signer.bat) $< $@",
        executable = True,
        target_compatible_with = ["@platforms//os:windows"],
        tools = ["scripts/signer.bat"],
        visibility = ["//visibility:public"],
    )
    for n, name in SIGNED_NAMES.items()
]

# Signatures of non-ASCII scripts break on Windows, see the script header.
sh_test(
    name = "signed_scripts_are_ascii",
    size = "small",
    srcs = ["scripts/check_ascii.sh"],
    args = ["$(rootpath %s)" % n for n in TO_SIGN_SCRIPTS] + [
        "$(rootpaths :msi_cmk_plugin_files)",
    ],
    data = TO_SIGN_SCRIPTS + [":msi_cmk_plugin_files"],
)

pkg_tar(
    name = "signed_plugins",
    srcs = [":sign_" + name for name in SIGNED_NAMES.values()],
    strip_prefix = "signed",
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:windows"],
    visibility = ["//visibility:public"],
)

# Unsigned collection of the same plugins, flattened to basenames. Used by the Azure
# signing path, which signs in the run.ps1 process (full environment + credentials)
# instead of inside Bazel actions. Bazel only gathers the files here - including the
# cross-package bakery-migrated plugins - and run.ps1 signs them and repacks the tar.
# Unsigned MSI builds (run.ps1 without signing, :msi_plugins without credentials)
# take their scripts from it too.
pkg_files(
    name = "unsigned_plugin_files",
    srcs = TO_SIGN_SCRIPTS,
    strip_prefix = strip_prefix.files_only(),
)

pkg_tar(
    name = "unsigned_plugins",
    srcs = [":unsigned_plugin_files"],
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

sh_library(
    name = "agents_windows_plugins_sh",
    srcs = [
        ".f12",
    ],
)

# Signed in the build via Azure Artifact Signing, for the MSI built on Linux.
# Needs --//bazel/rules:azure_signing_credentials_file, see sign_azure.bzl.
sign_tar_azure(
    name = "azure_signed_plugins",
    src = ":unsigned_plugins",
    tags = ["manual"],
)

# The scripts //agents/wnx:check_mk_agent_msi embeds: signed whenever signing
# credentials are given, like the MSI run.ps1 builds with --sign-azure.
alias(
    name = "msi_plugins",
    actual = select({
        "//bazel/rules:azure_signing_credentials_file_unset": ":unsigned_plugins",
        "//conditions:default": ":azure_signed_plugins",
    }),
    visibility = ["//agents/wnx:__pkg__"],
)
