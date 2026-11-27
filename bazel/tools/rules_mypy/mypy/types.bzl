# Modified by Checkmk GmbH, see bazel/tools/rules_mypy/VENDORED.md
"Extension for generating a types repository containing py_type_librarys for requirements."

load("//bazel/tools/rules_mypy/mypy/private:types.bzl", "generate")

requirements = tag_class(
    attrs = {
        "exclude_requirements": attr.string_list(default = [], mandatory = False),
        "name": attr.string(),
        "pip_requirements": attr.label(),
        "requirements_txt": attr.label(mandatory = True, allow_single_file = True),
    },
)

def _extension(module_ctx):
    for mod in module_ctx.modules:
        for tag in mod.tags.requirements:
            generate(
                name = tag.name,
                pip_requirements = tag.pip_requirements,
                requirements_txt = tag.requirements_txt,
                exclude_requirements = tag.exclude_requirements,
            )

types = module_extension(
    implementation = _extension,
    tag_classes = {
        "requirements": requirements,
    },
)
