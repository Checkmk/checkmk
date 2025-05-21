"""Provides commands for generating Typescript code from JSON files"""

load("@npm_cmk_shared_typing//packages/cmk-shared-typing:json-schema-to-typescript/package_json.bzl", json2ts = "bin")

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
