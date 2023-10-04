"""Define default foreign_cc framework commands. Linux platforms use bash"""

load(":commands.bzl", "FunctionAndCallInfo")

def shebang():
    return "#!/usr/bin/env bash"

def script_extension():
    return ".sh"

def pwd():
    return "$(pwd)"

def echo(text):
    return "echo \"{text}\"".format(text = text)

def export_var(name, value):
    return "export {name}={value}".format(name = name, value = value)

def local_var(name, value):
    return "local {name}={value}".format(name = name, value = value)

def use_var(name):
    return "$" + name

def env():
    return "env"

def path(expression):
    return "export PATH=\"{expression}:$PATH\"".format(expression = expression)

def touch(path):
    return "touch " + path

def enable_tracing():
    return "set -x"

def disable_tracing():
    return "set +x"

def mkdirs(path):
    return "mkdir -p " + path

def rm_rf(path):
    return "rm -rf " + path

def if_else(condition, if_text, else_text):
    return """
if [ {condition} ]; then
  {if_text}
else
  {else_text}
fi
""".format(condition = condition, if_text = if_text, else_text = else_text)

# buildifier: disable=function-docstring
def define_function(name, text):
    lines = []
    lines.append("function " + name + "() {")
    for line_ in text.splitlines():
        lines.append("  " + line_)
    lines.append("}")
    return "\n".join(lines)

def replace_in_files(dir, from_, to_):
    return FunctionAndCallInfo(
        text = """\
if [ -d "$1" ]; then
  SAVEIFS=$IFS
  IFS=$'\n'
  # Find all real files. Symlinks are assumed to be relative to something within the directory we're seaching and thus ignored
  local files=($(find -P "$1" \\( -type f -and \\( -name "*.pc" -or -name "*.la" -or -name "*-config" -or -name "*.mk" -or -name "*.cmake" \\) \\)))
  IFS=$SAVEIFS
  for file in ${files[@]+"${files[@]}"}; do
    local backup=$(mktemp)
    touch -r "${file}" "${backup}"
    sed -i 's@'"$2"'@'"$3"'@g' "${file}"
    if [[ "$?" -ne "0" ]]; then
      exit 1
    fi
    touch -r "${backup}" "${file}"
    rm "${backup}"
  done
fi
""",
    )

def copy_dir_contents_to_dir(source, target):
    return """cp -r --no-target-directory "{source}" "{target}" && find "{target}" -type f -exec touch -r "{source}" "{{}}" \\;""".format(
        source = source,
        target = target,
    )

def symlink_contents_to_dir(source, target):
    text = """\
if [[ -z "$1" ]]; then
  echo "arg 1 to symlink_contents_to_dir is unexpectedly empty"
  exit 1
fi
if [[ -z "$2" ]]; then
  echo "arg 2 to symlink_contents_to_dir is unexpectedly empty"
  exit 1
fi
local target="$2"
mkdir -p "$target"
if [[ -f "$1" ]]; then
  ##symlink_to_dir## "$1" "$target"
elif [[ -L "$1" ]]; then
  local actual=$(readlink "$1")
  ##symlink_contents_to_dir## "$actual" "$target"
elif [[ -d "$1" ]]; then
  SAVEIFS=$IFS
  IFS=$'\n'
  local children=($(find -H "$1" -maxdepth 1 -mindepth 1))
  IFS=$SAVEIFS
  for child in "${children[@]:-}"; do
    ##symlink_to_dir## "$child" "$target"
  done
fi
"""
    return FunctionAndCallInfo(text = text)

def symlink_to_dir(source, target):
    text = """\
if [[ -z "$1" ]]; then
  echo "arg 1 to symlink_to_dir is unexpectedly empty"
  exit 1
fi
if [[ -z "$2" ]]; then
  echo "arg 2 to symlink_to_dir is unexpectedly empty"
  exit 1
fi
local target="$2"
mkdir -p "$target"
if [[ -f "$1" ]]; then
  # In order to be able to use `replace_in_files`, we ensure that we create copies of specfieid
  # files so updating them is possible.
  if [[ "$1" == *.pc || "$1" == *.la || "$1" == *-config || "$1" == *.mk || "$1" == *.cmake ]]; then
    dest="$target/$(basename \"$1\")"
    cp "$1" "$dest" && chmod +w "$dest" && touch -r "$1" "$dest"
  else
    ln -sf "$1" "$target/${1##*/}"
  fi
elif [[ -L "$1" && ! -d "$1" ]]; then
  cp -pR "$1" "$2"
elif [[ -d "$1" ]]; then
  SAVEIFS=$IFS
  IFS=$'\n'
  local children=($(find -H "$1" -maxdepth 1 -mindepth 1))
  IFS=$SAVEIFS
  local dirname=$(basename "$1")
  mkdir -p "$target/$dirname"
  for child in "${children[@]:-}"; do
    if [[ -n "$child" && "$dirname" != *.ext_build_deps ]]; then
      ##symlink_to_dir## "$child" "$target/$dirname"
    fi
  done
else
  echo "Can not copy $1"
fi
"""
    return FunctionAndCallInfo(text = text)

def script_prelude():
    return "set -euo pipefail"

def increment_pkg_config_path(source):
    text = """\
local children=$(find "$1" -mindepth 1 -name '*.pc')
# assume there is only one directory with pkg config
for child in $children; do
  export PKG_CONFIG_PATH="$${PKG_CONFIG_PATH:-}$$:$(dirname $child)"
  return
done
"""
    return FunctionAndCallInfo(text = text)

def cat(filepath):
    return "cat \"{}\"".format(filepath)

def redirect_out_err(from_process, to_file):
    return from_process + " &> " + to_file

def assert_script_errors():
    return "set -e"

def cleanup_function(on_success, on_failure):
    text = "\n".join([
        "local ecode=$?",
        "if [ $ecode -eq 0 ]; then",
        on_success,
        "else",
        on_failure,
        "fi",
    ])
    return FunctionAndCallInfo(text = text, call = "trap \"cleanup_function\" EXIT")

def children_to_path(dir_):
    text = """\
if [ -d {dir_} ]; then
  local tools=$(find "$EXT_BUILD_DEPS/bin" -maxdepth 1 -mindepth 1)
  for tool in $tools;
  do
    if  [[ -d \"$tool\" ]] || [[ -L \"$tool\" ]]; then
      export PATH=$PATH:$tool
    fi
  done
fi""".format(dir_ = dir_)
    return FunctionAndCallInfo(text = text)

def define_absolute_paths(dir_, abs_path):
    return "##replace_in_files## {dir_} {REPLACE_VALUE} {abs_path}".format(
        dir_ = dir_,
        REPLACE_VALUE = "\\${EXT_BUILD_DEPS}",
        abs_path = abs_path,
    )

def replace_absolute_paths(dir_, abs_path):
    return "##replace_in_files## {dir_} {abs_path} {REPLACE_VALUE}".format(
        dir_ = dir_,
        REPLACE_VALUE = "\\${EXT_BUILD_DEPS}",
        abs_path = abs_path,
    )

def define_sandbox_paths(dir_, abs_path):
    return "##replace_in_files## {dir_} {REPLACE_VALUE} {abs_path}".format(
        dir_ = dir_,
        REPLACE_VALUE = "\\${EXT_BUILD_ROOT}",
        abs_path = abs_path,
    )

def replace_sandbox_paths(dir_, abs_path):
    return "##replace_in_files## {dir_} {abs_path} {REPLACE_VALUE}".format(
        dir_ = dir_,
        REPLACE_VALUE = "\\${EXT_BUILD_ROOT}",
        abs_path = abs_path,
    )

def replace_symlink(file):
    return ""

commands = struct(
    assert_script_errors = assert_script_errors,
    cat = cat,
    children_to_path = children_to_path,
    cleanup_function = cleanup_function,
    copy_dir_contents_to_dir = copy_dir_contents_to_dir,
    define_absolute_paths = define_absolute_paths,
    define_function = define_function,
    define_sandbox_paths = define_sandbox_paths,
    disable_tracing = disable_tracing,
    echo = echo,
    enable_tracing = enable_tracing,
    env = env,
    export_var = export_var,
    if_else = if_else,
    increment_pkg_config_path = increment_pkg_config_path,
    local_var = local_var,
    mkdirs = mkdirs,
    path = path,
    pwd = pwd,
    redirect_out_err = redirect_out_err,
    replace_absolute_paths = replace_absolute_paths,
    replace_in_files = replace_in_files,
    replace_sandbox_paths = replace_sandbox_paths,
    replace_symlink = replace_symlink,
    rm_rf = rm_rf,
    script_extension = script_extension,
    script_prelude = script_prelude,
    shebang = shebang,
    symlink_contents_to_dir = symlink_contents_to_dir,
    symlink_to_dir = symlink_to_dir,
    touch = touch,
    use_var = use_var,
)
