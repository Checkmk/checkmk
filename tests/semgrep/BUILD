load("@rules_uv//uv:pip.bzl", "pip_compile")
load("@rules_uv//uv:venv.bzl", "create_venv")
load("//:bazel_variables.bzl", "UV_PIP_COMPILE_ARGS", "UV_VENV_ARGS")

exports_files([
    "requirements.txt",
])

pip_compile(
    name = "requirements_lock",
    args = UV_PIP_COMPILE_ARGS,
    requirements_in = ":requirements.txt",
    requirements_txt = ":requirements_lock.txt",
)

create_venv(
    name = "venv",
    destination_folder = "tests/semgrep/.venv",
    requirements_txt = ":requirements_lock.txt",
    uv_args = UV_VENV_ARGS,
)
