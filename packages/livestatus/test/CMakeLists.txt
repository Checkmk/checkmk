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

# <test> target
enable_testing()

add_executable(
  test
  test.cc
  test_AttributeListColumn.cc
  test_BlobColumn.cc
  test_BoolColumn.cc
  test_DoubleColumn.cc
  test_FileSystemHelper.cc
  test_IntColumn.cc
  test_ListColumn.cc
  test_LogEntry.cc
  test_Mangling.cc
  test_Metric.cc
  test_RegExp.cc
  test_Renderer.cc
  test_Queue.cc
  test_StringColumn.cc
  test_StringUtil.cc
  test_TimeColumn.cc)

target_include_directories(test PUBLIC ../include ${googletest_ext_include})
target_compile_features(test PRIVATE cxx_std_17)
target_link_options(test PRIVATE -rdynamic -static-libstdc++)
target_link_libraries(test PRIVATE livestatus pthread stdc++ GTest::gtest_main)

include(GoogleTest)
gtest_discover_tests(test)
