cmake_minimum_required(VERSION 3.24)

set(root_repo_dir ${CMAKE_CURRENT_SOURCE_DIR}/../..)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(PLANTUTML_VERSION 1.2022.13)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_COMPILER g++-13) # TODO: replace with more intelligent approach

set(CMK_VERSION 2.3.0p26)
string(REGEX REPLACE "([0-9]+)\.([0-9]+)\.([0-9]+).*" "\\1.\\2.\\3"
                     MANGLED_VERSION ${CMK_VERSION})

add_compile_options(
  -Wall
  -Wextra
  -Werror
  -DHAVE_RE2
  -DASIO_DISABLE_CONCEPTS
  -DASIO_NO_DEPRECATED
  -fPIC
  -gdwarf-4
  -O3)

project(
  neb
  VERSION ${MANGLED_VERSION}
  DESCRIPTION "Livestatus NEB"
  LANGUAGES CXX)

add_subdirectory(src)
add_subdirectory(test)
