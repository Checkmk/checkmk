load("@rules_pkg//pkg:mappings.bzl", "pkg_files", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

CHECK_MK_LANGUAGES = [
    "de",
    "es",
    "fr",
    "it",
    "ja",
    "nl",
    "pt_PT",
    "ro",
]

filegroup(
    name = "po_files",
    srcs = ["%s/LC_MESSAGES/multisite.po" % lang for lang in CHECK_MK_LANGUAGES],
    visibility = ["//packages/cmk-frontend-vue:__pkg__"],
)

[genrule(
    name = "compile_mo_file_for_%s" % lang,
    srcs = ["%s/LC_MESSAGES/multisite.po" % lang],
    outs = ["%s/LC_MESSAGES/multisite.mo" % lang],
    cmd = "msgfmt -v -o $@ $<",
) for lang in CHECK_MK_LANGUAGES]

pkg_files(
    name = "mo_files_pkg",
    srcs = [":%s/LC_MESSAGES/multisite.mo" % lang for lang in CHECK_MK_LANGUAGES] +
           ["%s/alias" % lang for lang in CHECK_MK_LANGUAGES],
    prefix = "share/check_mk/locale",
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_tar(
    name = "locale",
    srcs = [
        "mo_files_pkg",
    ],
    visibility = ["//omd:__pkg__"],
)
