"""Module extension declaring external archives for the PowerShell linter.

pwsh, PSScriptAnalyzer, and ConvertToSARIF are not on the Bazel Central
Registry; bzlmod disallows http_archive directly in MODULE.bazel so they
live here as a module extension.

Versions and sha256 values match aspect-build/rules_lint#850 verbatim.
"""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def _repos_impl(_mctx):
    http_archive(
        name = "pwsh",
        url = "https://github.com/PowerShell/PowerShell/releases/download/v7.6.1/powershell-7.6.1-linux-x64.tar.gz",
        sha256 = "dfc94229767921603f7c3e1cb1ac5aa931448af7496ccf657723b6278057c415",
        build_file_content = """exports_files(["pwsh"])""",
        # The upstream tarball ships `pwsh` without the execute bit; set it here.
        patch_cmds = ["chmod +x pwsh"],
    )
    http_archive(
        name = "psscriptanalyzer",
        url = "https://www.powershellgallery.com/api/v2/package/PSScriptAnalyzer/1.25.0",
        sha256 = "14e634c828eb98efb9f40b2918ba90f139ed5eccdf663a2a747736d996995d60",
        # PSGallery serves a .nupkg (zip); the URL has no extension so be explicit.
        type = "zip",
        build_file_content = """
package(default_visibility = ["//visibility:public"])
filegroup(name = "files", srcs = glob(["**"]))
""",
    )
    http_archive(
        name = "converttosarif",
        url = "https://www.powershellgallery.com/api/v2/package/ConvertToSARIF/1.0.0",
        sha256 = "b1bdf60f029f12284dd78b2c2edc34705d4475079b4cb3d50d669da464bf3d35",
        type = "zip",
        build_file_content = """
package(default_visibility = ["//visibility:public"])
filegroup(name = "files", srcs = glob(["**"]))
""",
    )

repos = module_extension(
    implementation = _repos_impl,
)
