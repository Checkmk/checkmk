"""Provides commands for generating Python and Typescript code from JSON files"""

load("@aspect_bazel_lib//lib:run_binary.bzl", "run_binary")
load("@aspect_rules_js//js:defs.bzl", "js_run_binary")
load("//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")

_DATAMODEL_CODEGEN = Label("//bazel/tools/shared_typing:datamodel_codegen")
_JSON2TS = Label("//bazel/tools/shared_typing:json2ts")

JSON2PYTHON_LITERAL_ENUM_ARGS = [
    "--use-field-description",
    "--use-title-as-name",
    "--use-double-quotes",
    "--use-default",
    "--formatters=builtin",
    "--custom-formatters=utils.format",
    "--output-model-type=dataclasses.dataclass",
    "--enum-field-as-literal=all",
    "--use-generic-container-types",
    "--frozen-dataclasses",
    "--keyword-only",
    "--use-union-operator",
    # Append an underscore to enum members clashing with a str method, e.g.
    # "count_". Despite its name, this is needed for StrEnum, too.
    "--use-subclass-enum",
    # Fields with a default never become None. Despite its help text, this
    # works for JSON Schema, too.
    "--strict-nullable",
]

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
        js_run_binary(
            name = "{}_{}".format(name, src.replace(".json", "")),
            tool = _JSON2TS,
            mnemonic = "Json2Typescript",
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

def json2python(name, srcs, data, extra_args, source_dir, target_dir):
    """Create Python files from .json files using `datamodel-code-generator`

    Args:
      name: name of the generated `filegroup` containing the output
      srcs: list of .json files to be processed
      data: additional files needed to successfully call `datamodel-code-generator`
      extra_args: additional arguments propagated to `datamodel-code-generator`
      source_dir: directory with .json files - relative for referenced files
      target_dir: relative path for Python files to be created to
    """
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
            tool = _DATAMODEL_CODEGEN,
            mnemonic = "Json2Python",
        )
        output_names.append(":" + out_path)

    native.filegroup(
        name = name,
        srcs = output_names,
    )
