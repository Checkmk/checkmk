# The target is not generated automatically with full build: this is 
# intended, because documentation is to be generated separately from 
# the main build

find_package(Doxygen REQUIRED dot)

if (DOXYGEN_FOUND)
  message( "Doxygen will use ${PROJECT_SOURCE_DIR} as a base")
  message( "run `cmake --build build -t documentation` to create documentation")

  set(DOXYGEN_GENERATE_HTML YES)
  set(DOXYGEN_GENERATE_MAN NO)

  file(DOWNLOAD "https://master.dl.sourceforge.net/project/plantuml/${PLANTUTML_VERSION}/plantuml.${PLANTUTML_VERSION}.jar" "${CMAKE_CURRENT_SOURCE_DIR}/plantuml.jar")
  # see https://discourse.cmake.org/t/how-to-set-plantuml-jar-path/3021
  set(DOXYGEN_PLANTUML_JAR_PATH "${CMAKE_CURRENT_SOURCE_DIR}/plantuml.jar")

  doxygen_add_docs(
    documentation
    ${CMAKE_CURRENT_SOURCE_DIR}/startpage.md    
    ${PROJECT_SOURCE_DIR}/src
    ${PROJECT_SOURCE_DIR}/include/livestatus
  )
else (DOXYGEN_FOUND)
  message("Doxygen need to be installed to generate the doxygen documentation")
endif (DOXYGEN_FOUND)