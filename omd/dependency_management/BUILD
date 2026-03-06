load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@bazel_skylib//rules:copy_file.bzl", "copy_file")
load("@bazel_skylib//rules:run_binary.bzl", "run_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load(":dependency_management.bzl", "bill_of_materials", "dependency_list")

py_binary(
    name = "list_dependencies_bin",
    srcs = [
        "cyclonedx.py",
        "list_dependencies.py",
        "pnpm_parser.py",
    ],
    imports = ["."],
    main = "list_dependencies.py",
    visibility = ["//omd:__subpackages__"],
    deps = [
        requirement("pydantic"),
        requirement("pyyaml"),
        requirement("toml"),
    ],
)

py_binary(
    name = "bill_of_materials_bin",
    srcs = [
        "create_bom.py",
        "cyclonedx.py",
    ],
    data = [
        "automatically_researched_licenses.json",
        "manually_researched_licenses.json",
    ],
    imports = ["."],
    main = "create_bom.py",
    visibility = ["//omd:__subpackages__"],
    deps = [
        requirement("pydantic"),
        requirement("pyyaml"),
    ],
)

bill_of_materials(
    name = "bill_of_materials",
    dependencies = ":list_of_dependencies",
    vulnerability_info = "vulnerability_info.yml",
)

py_binary(
    name = "research_licenses",
    srcs = [
        "cyclonedx.py",
        "research_licenses.py",
    ],
    args = [
        "--dependencies",
        "$(location list_of_dependencies)",
        "--out",
        "$(location automatically_researched_licenses.json)",
    ],
    data = [
        "automatically_researched_licenses.json",
        "manually_researched_licenses.json",
        ":list_of_dependencies",
    ],
    imports = ["."],
    main = "research_licenses.py",
    deps = [
        requirement("pydantic"),
        requirement("pyspdx"),
        requirement("requests"),
    ],
)

dependency_list(
    name = "list_of_dependencies",
    manifest_srcs = [
        "//:Cargo.lock",
        "//:pnpm-lock.yaml",
        "//:runtime-requirements.txt",
    ],
    sbom_target = "//omd:deps_packages_base",
)

py_binary(
    name = "generate_bom_csv_py",
    srcs = ["generate_bom_csv.py"],
)

run_binary(
    name = "generate_bom_csv",
    srcs = [":bill_of_materials"],
    outs = ["bill-of-materials.csv"],
    args = [
        "--bom",
        "$(location :bill_of_materials)",
        "--out",
        "$(location bill-of-materials.csv)",
    ],
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
)

# We used to ship it with the dashes, let's keep that
copy_file(
    name = "bill_of_materials_renamed",
    src = ":bill_of_materials",
    out = "bill-of-materials.json",
)

pkg_tar(
    name = "license_info",
    srcs = [
        "bill-of-materials.csv",
        ":bill_of_materials_renamed",
        ":build_bom_texts_pdf",
    ],
    package_dir = "share/doc/",
    package_file_name = "license_info_archive.tar",
    stamp = 1,
    visibility = ["//omd:__subpackages__"],
)
