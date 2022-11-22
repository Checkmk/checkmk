cmake_minimum_required(VERSION 3.20)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_VERBOSE_MAKEFILE ON)

project(
  Livestatus
  VERSION 0.1
  DESCRIPTION "Livestatus library"
  LANGUAGES CXX)

add_subdirectory(src)
add_subdirectory(loader)
