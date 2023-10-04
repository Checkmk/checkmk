include(FetchContent)

FetchContent_Declare(
  gtest-omd
  URL ${root_repo_dir}/third_party/googletest/googletest-71140c3ca7-patched.tar.gz
  URL_HASH
    SHA256=ff90c74541157daf5fe7503b2b02ddc1b1df35bd5d2d861e9865aa4bd53248ce
  DOWNLOAD_EXTRACT_TIMESTAMP no)
FetchContent_MakeAvailable(gtest-omd)
FetchContent_GetProperties(
  gtest-omd
  SOURCE_DIR src_dir
  BINARY_DIR bin_dir
  POPULATED done_var)
set(googletest_ext_include ${src_dir}/googletest/include)

include(ExternalProject)

# <test> target
enable_testing()

add_executable(
  test
  DummyNagios.cc
  TableQueryHelper.cc
  TableQueryHelper.h
  test_CrashReport.cc
  test_DictFilter.cc
  test_MacroExpander.cc
  test_utilities.cc
  test_utilities.h)

add_executable(NagiosMockup NagiosMockup.cc)
target_include_directories(NagiosMockup PRIVATE ../include)
target_link_options(NagiosMockup PRIVATE -rdynamic -static-libstdc++)
target_link_libraries(NagiosMockup PRIVATE neb pthread stdc++)
add_dependencies(test NagiosMockup)

target_include_directories(test PUBLIC ../include ${googletest_ext_include})
target_compile_features(test PRIVATE cxx_std_17)
target_link_options(test PRIVATE -rdynamic -static-libstdc++)
target_link_libraries(test PRIVATE neb pthread stdc++ GTest::gtest_main)

include(GoogleTest)
gtest_discover_tests(test)
