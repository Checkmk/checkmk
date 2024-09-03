load("@rules_python//python:pip.bzl", "compile_pip_requirements")

genrule(
    name = "_generate_requirements_in",
    srcs = [
        "@//:Pipfile",
        "@//:Pipfile.lock",
    ],
    outs = ["requirements_in.orig"],
    # We need to filter out editable reqs are the relative paths are not
    # accessible in the sandbox.  Failing to do so raises an `InstallationError`.
    cmd = "pipenv requirements --dev | grep -Ev '^\\-e[[:space:]]' > $@",
)

FILTER_OUT = [
    # Provided elsewhere
    "rrdtool",
    "protobuf",
    # Broken, see https://github.com/NetApp/ontap-rest-python/issues/46
    "netapp-ontap",
]

genrule(
    name = "_prune_requirements_in",
    srcs = ["requirements_in.orig"],
    outs = ["requirements_in.txt"],
    cmd = "cat $< | grep -v " + " ".join([("-e ^%s==" % pkg) for pkg in FILTER_OUT]) + " > $@",
)

compile_pip_requirements(
    name = "requirements",
    requirements_in = "requirements_in.txt",
    requirements_txt = "@//:requirements_lock.txt",
)
