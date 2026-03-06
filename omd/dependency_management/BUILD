load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@bazel_skylib//rules:run_binary.bzl", "run_binary")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

py_binary(
    name = "generate_bom_csv_py",
    srcs = ["generate_bom_csv.py"],
    tags = ["manual"],
)

run_binary(
    name = "generate_bom_csv",
    srcs = ["//omd:bill-of-materials.json"],
    outs = ["bill-of-materials.csv"],
    args = [
        "--bom",
        "$(location //omd:bill-of-materials.json)",
        "--out",
        "$(location bill-of-materials.csv)",
    ],
    tags = ["manual"],
    tool = ":generate_bom_csv_py",
)

run_binary(
    name = "build_bom_texts_pdf",
    srcs = [":generate_bom_csv"],
    outs = ["License_texts.pdf"],
    args = [
        "--pdf",
        "$(location License_texts.pdf)",
        "--csv",
        "$(location :generate_bom_csv)",
    ],
    tags = ["manual"],
    tool = ":build_bom_texts_pdf_py",
)

py_binary(
    name = "build_bom_texts_pdf_py",
    srcs = ["build_bom_texts_pdf.py"],
    data = [
        "Calibri.ttf",
        "checkmk_logo.svg",
        ":license_texts",
    ],
    tags = ["manual"],
    deps = [
        requirement("reportlab"),
        requirement("svglib"),
    ],
)

filegroup(
    name = "license_texts",
    srcs = glob([
        "license_texts/*.txt",
    ]),
    tags = ["manual"],
)

BOM_ARTIFACTS = [
    "bill-of-materials.json",
    "bill-of-materials.csv",
    "License_texts.pdf",
]

[write_file(
    name = file + "_write",
    out = file + ".faked",
    content = ["This artifact was faked during the build process by bazel."],
    visibility = ["//omd:__subpackages__"],
) for file in BOM_ARTIFACTS]

pkg_tar(
    name = "license_info",
    srcs = select({
        # ToDo: Build BOM in the same Workspace
        "@//:use_fake_artifacts_enabled": [file + ".faked" for file in BOM_ARTIFACTS],
        "//conditions:default": [
            "License_texts.pdf",
            "bill-of-materials.csv",
            "//omd:bill-of-materials.json",
        ],
    }),
    package_dir = "share/doc/",
    package_file_name = "license_info_archive.tar",
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__subpackages__"],
)
