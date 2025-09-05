load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def patch(version_str, sha256):
    filename = "patch-" + version_str + ".tar.gz"
    http_archive(
        name = "patch",
        urls = [
            # Fast mirror located nearby, see https://www.gnu.org/prep/ftp.en.html
            "https://ftpmirror.gnu.org/gnu/patch/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
        patches = [
            "//omd/packages/patch/patches:ed-style-01-missing-input-files.patch.dif",
            "//omd/packages/patch/patches:ed-style-02-fix-arbitrary-command-execution.patch.dif",
            "//omd/packages/patch/patches:ed-style-03-update-test-Makefile.patch.dif",
            "//omd/packages/patch/patches:ed-style-04-invoke-ed-directly.patch.dif",
            "//omd/packages/patch/patches:ed-style-05-minor-cleanups.patch.dif",
            "//omd/packages/patch/patches:ed-style-06-fix-test-failure.patch.dif",
            "//omd/packages/patch/patches:ed-style-07-dont-leak-tmp-file.patch.dif",
            "//omd/packages/patch/patches:ed-style-08-dont-leak-tmp-file-multi.patch.dif",
            "//omd/packages/patch/patches:fix-segfault-mangled-rename.patch.dif",
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        build_file = "@omd_packages//omd/packages/patch:BUILD.patch",
        strip_prefix = "patch-" + version_str,
    )
