"""The mypy version for the Bazel aspect and the venv."""

# The mypy aspect runs mypy from its own lock, bazel/tools/mypy-requirements.txt, so that routine
# updates of requirements.txt, which bump mypy's helper packages (librt, ast-serialize, pathspec)
# more often than mypy itself, don't re-run all mypy actions. Bump mypy here, then re-lock both:
#   bazel run //bazel/tools:mypy_requirements
#   bazel run //:lock_python_requirements
MYPY_VERSION = "2.4.1"
