cmake_minimum_required(VERSION 3.24)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(PLANTUTML_VERSION 1.2022.13)
set(CMAKE_CXX_COMPILER g++-12) # TODO: replace with more intelligent approach
set(root_repo_dir ${CMAKE_CURRENT_SOURCE_DIR}/../..)
add_compile_options(
  -Wall
  -Wextra
  -Werror
  -DHAVE_RE2
  -fPIC
  -gdwarf-4
  -std=c++17
  -O3)

project(
  neb
  VERSION 2.3.0
  DESCRIPTION "Livestatus NEB"
  LANGUAGES CXX)

# SUB-DIRS:
add_subdirectory(src)
add_subdirectory(test)
