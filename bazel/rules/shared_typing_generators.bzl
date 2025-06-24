"""Provides commands for generating Python and Typescript code from JSON files"""

load("@bazel_skylib//rules:run_binary.bzl", "run_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@npm_cmk_shared_typing//packages/cmk-shared-typing:json-schema-to-typescript/package_json.bzl", json2ts = "bin")
load("@omd_packages//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")

def json2typescript(name, srcs, header_txt, data, chdir, source_dir, target_dir):
    """Create Typescript files from .json files using `json2ts`

    Args:
      name: name of the generated `filegroup` containing the output
      srcs: list of .json files to be processed
      header_txt: goes to generated file header
      data: additional files needed to successfully call json2ts
      chdir: relative directory to be executed in
      source_dir: directory with .json files - relative for referenced files
      target_dir: relative path for TS files to be created to
    """
    output_names = []

    for src in srcs:
        src_path = "{}/{}".format(source_dir, src)
        out_path = "{}/{}".format(target_dir, src.replace(".json", ".ts"))
        json2ts.json2ts(
            name = "{}_{}".format(name, src.replace(".json", "")),
            srcs = data,
            outs = [out_path],
            args = [
                "--additionalProperties=false",
                "--declareExternallyReferenced",
                '--bannerComment="{}"'.format(header_txt),
                "--cwd {}".format(source_dir),
                "--input {}".format(src_path),
                "--output {}".format(out_path),
            ],
            chdir = chdir,
        )
        output_names.append(":" + out_path)

    native.filegroup(
        name = name,
        srcs = output_names,
    )

def json2python(name, srcs, data, formatter, extra_args, source_dir, target_dir):
    """Create Python files from .json files using `datamodel-code-generator`

    Args:
      name: name of the generated `filegroup` containing the output
      srcs: list of .json files to be processed
      data: additional files needed to successfully call `datamodel-code-generator`
      formatter: label to a `py_library()` instance containing the `utils.format` package
      extra_args: additional arguments propagated to `datamodel-code-generator`
      source_dir: directory with .json files - relative for referenced files
      target_dir: relative path for Python files to be created to
    """
    py_console_script_binary(
        name = "{}_generator".format(name),
        pkg = requirement("datamodel-code-generator"),
        script = "datamodel-codegen",
        deps = [
            formatter,
            requirement("libcst"),
        ],
    )

    output_names = []

    for src in srcs:
        src_path = "{}/{}".format(source_dir, src)
        out_path = "{}/{}".format(target_dir, src.replace(".json", ".py"))

        run_binary(
            name = "{}_{}".format(name, src.replace(".json", "")),
            srcs = data,
            outs = [out_path],
            args = [
                "--input=$(location :{})".format(src_path),
                "--input-file-type=jsonschema",
                "--output=$(location :{})".format(out_path),
                "--target-python-version={}".format(PYTHON_MAJOR_DOT_MINOR),
            ] + extra_args,
            tool = ":{}_generator".format(name),
        )
        output_names.append(":" + out_path)

    native.filegroup(
        name = name,
        srcs = output_names,
    )
