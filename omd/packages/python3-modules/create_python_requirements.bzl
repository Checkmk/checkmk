load("//omd/packages/python3-modules:parse-requirements.bzl", parse_requirements = "parse")

BUILD_FILE_CONTENTS = """\
package(default_visibility = ["//visibility:public"])

# Ensure the `requirements.bzl` source can be accessed by stardoc, since users load() from it
exports_files(["requirements.bzl"])
"""

def _create_python_requirements_impl(rctx):
    rctx.file("BUILD.bazel", BUILD_FILE_CONTENTS)

    # Create the requirements from Pipfile.lock
    # At the moment there might be a pitfall, as `python_requirements.bzl`
    # has to be created before any target can be built. So we can not
    # use our own Python.
    pipfile_path = rctx.path(Label(rctx.attr.requirements))
    content = rctx.execute(
        ["pipenv", "requirements", "--hash"],
        environment = {
            "PIPENV_PIPFILE": str(pipfile_path),
        },
        quiet = False,
    )

    parsed_requirements_txt = parse_requirements(content.stdout)

    packages = {
        name: requirement
        for name, requirement in parsed_requirements_txt.requirements
        if name not in rctx.attr.ignored_modules
    }

    bzl_packages = sorted(packages.keys())

    rctx.template(
        "requirements.bzl",
        Label("//omd/packages/python3-modules:python_requirements.bzl.tmpl"),
        substitutions = {
            "%%ALL_REQUIREMENTS%%": str(bzl_packages),
            "%%NAME%%": rctx.attr.name,
            "%%PACKAGES%%": str(packages),
        },
    )

create_python_requirements = repository_rule(
    attrs = {"requirements": attr.string(mandatory = True), "ignored_modules": attr.string_list()},
    doc = """A rule for importing `Pipfile` dependencies into Bazel.""",
    implementation = _create_python_requirements_impl,
)
