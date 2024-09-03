load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def mod_fcgid_workspace():
    version_str = "2.3.9"
    filename = "mod_fcgid-" + version_str + ".tar.gz"
    http_archive(
        name = "mod_fcgid",
        build_file = "@omd_packages//omd/packages/mod_fcgid:BUILD.mod_fcgid.bazel",
        strip_prefix = "mod_fcgid-" + version_str,
        urls = [
            "https://downloads.apache.org/httpd/mod_fcgid/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        patches = [
            "//omd/packages/mod_fcgid/patches:0001-fcgid_proc_unix.c.dif",
            "//omd/packages/mod_fcgid/patches:0002-fcgid_pm_unix.c.dif",
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        sha256 = "1cbad345e3376b5d7c8f9a62b471edd7fa892695b90b79502f326b4692a679cf",
    )
