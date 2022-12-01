cmake_minimum_required(VERSION 3.20)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_VERBOSE_MAKEFILE ON)
set(PLANTUTML_VERSION 1.2022.13)
set(CMAKE_CXX_COMPILER g++-12) # TODO: replace with more intelligent approach
set(root_repo_dir ${CMAKE_CURRENT_SOURCE_DIR}/../..)

project(
  Livestatus
  VERSION 0.1
  DESCRIPTION "Livestatus library"
  LANGUAGES CXX)

# TOOLING:
find_package(Python3 REQUIRED)
message("Found python3: ${Python3_EXECUTABLE}")

find_program(
  iwyu_tool_path
  NAMES iwyu_tool.py
  PATHS ${root_repo_dir}/scripts)
message("iwyu_tool_path: ${iwyu_tool_path} in ${root_repo_dir}/scripts")

find_program(
  run_clang_tidy_path
  NAMES run-clang-tidy.py
  PATHS ${root_repo_dir}/scripts)
message("run-clang-tidy: ${run_clang_tidy_path} in ${root_repo_dir}/scripts")

# SUB-DIRS:
add_subdirectory(src)
add_subdirectory(test)
add_subdirectory(doc)
