# buildifier: disable=module-docstring # would break BOM dependency scanner otherwise
# PYTHON_VERSION and PYTHON_VERSION_WINDOWS are sed-ed into defines.make.
# This file won't be necessary anymore when we finished porting
# to rules_py.
PYTHON_VERSION = "3.13.13"

# The python version used in the windows agent modules is kept separate from
# PYTHON_VERSION as they are not directly connected, but should stay as close
# as possible.
PYTHON_VERSION_WINDOWS = "3.13.13"
