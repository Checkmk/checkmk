include(ExternalProject)

set(gtest_prefix "${CMAKE_CURRENT_BINARY_DIR}/gtest")
ExternalProject_Add(
  gtest-external
  URL ${root_repo_dir}/omd/packages/googletest/googletest-9c332145b7.tar.gz
  URL_HASH
    SHA256=f69e29721c09b3a4b9820a76236b7f230aef157527951eb4e8a3a6ec601fda22
  PREFIX "${gtest_prefix}"
  INSTALL_COMMAND "" DOWNLOAD_EXTRACT_TIMESTAMP no
  CMAKE_ARGS -DCMAKE_CXX_COMPILER=g++-12)

set(gtest_libs "${gtest_prefix}/src/gtest-external-build/lib")
set(gtest_includes "${gtest_prefix}/src/gtest-external/googletest/include")

# Import location variables for the generated gtest and gtest_main libraries
set(gtest_imported_location
    IMPORTED_LOCATION
    "${gtest_libs}/${CMAKE_STATIC_LIBRARY_PREFIX}gtest${CMAKE_STATIC_LIBRARY_SUFFIX}"
)
set(gtest_main_imported_location
    IMPORTED_LOCATION
    "${gtest_libs}/${CMAKE_STATIC_LIBRARY_PREFIX}gtest_main${CMAKE_STATIC_LIBRARY_SUFFIX}"
)

# the gtest include dir is created during build, but it is required to the
# set_target_properties call below, so make it to avoid an error
file(MAKE_DIRECTORY ${gtest_includes})

add_library(gtest IMPORTED STATIC GLOBAL)
set_target_properties(
  gtest
  PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "${gtest_includes}"
             IMPORTED_LINK_INTERFACE_LIBRARIES "${CMAKE_THREAD_LIBS_INIT}"
             ${gtest_imported_location})

add_library(gtest_main IMPORTED STATIC GLOBAL)
set_target_properties(
  gtest_main PROPERTIES IMPORTED_LINK_INTERFACE_LIBRARIES gtest
                        ${gtest_main_imported_location})
add_dependencies(gtest gtest-external)

# <test> target
enable_testing()

add_executable(test test.cc)

target_include_directories(test PUBLIC ../include ${gtest_includes})
target_compile_features(test PRIVATE cxx_std_17)
target_link_options(test PRIVATE -rdynamic)
target_link_libraries(test PRIVATE livestatus pthread stdc++ gtest_main)

include(GoogleTest)
gtest_discover_tests(test)
