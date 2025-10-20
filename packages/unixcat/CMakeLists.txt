cmake_minimum_required(VERSION 3.24)

set(root_repo_dir ${CMAKE_CURRENT_SOURCE_DIR}/../..)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(PLANTUTML_VERSION 1.2022.13)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_COMPILER g++-14) # TODO: replace with more intelligent approach

add_compile_options(
  -Wall
  -Wextra
  -Werror
  -Wno-deprecated-declarations
  -DHAVE_RE2
  -fPIC
  -gdwarf-4
  -O3)

project(
  unixcat
  VERSION 1.0
  DESCRIPTION "unixcat"
  LANGUAGES CXX)

add_subdirectory(src)
add_subdirectory(test)
