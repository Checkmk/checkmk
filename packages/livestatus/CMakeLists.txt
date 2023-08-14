cmake_minimum_required(VERSION 3.24)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_COMPILER g++-13) # TODO: replace with more intelligent approach
set(root_repo_dir ${CMAKE_CURRENT_SOURCE_DIR}/../..)
add_compile_options(
  -Wall
  -Wextra
  -Werror
  -DHAVE_RE2
  -DASIO_DISABLE_CONCEPTS
  -DASIO_NO_DEPRECATED
  -fPIC
  -gdwarf-4
  -std=c++17
  -O3)

project(
  Livestatus
  VERSION 0.1
  DESCRIPTION "Livestatus library"
  LANGUAGES CXX)

# SUB-DIRS:
add_subdirectory(src)
add_subdirectory(test)
