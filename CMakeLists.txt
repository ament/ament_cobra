cmake_minimum_required(VERSION 3.16)
project(cobra_vendor NONE)

find_package(ament_cmake REQUIRED)

set(extra_cmake_args)

if(DEFINED CMAKE_BUILD_TYPE)
  list(APPEND extra_cmake_args "-DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}")
endif()

include(ExternalProject)
ExternalProject_Add(cobra-3.6
  PREFIX cobra-3.6
  GIT_REPOSITORY https://github.com/nimble-code/cobra
  GIT_TAG ab06e676f9123ec07011a09c38daffaa4fbfdc60
  INSTALL_DIR <SOURCE_DIR>/cobra_install
  BUILD_IN_SOURCE TRUE
  CONFIGURE_COMMAND ""
  BUILD_COMMAND
  ${CMAKE_COMMAND} -E chdir <SOURCE_DIR>/src make linux && ${CMAKE_COMMAND} -E chdir <SOURCE_DIR>/src_app make all
  INSTALL_COMMAND
  ${CMAKE_COMMAND} -E chdir <SOURCE_DIR>/src make install_linux MAN=/dev/null && ${CMAKE_COMMAND} -E chdir <SOURCE_DIR>/src_app make install_linux
)

install(PROGRAMS
  ${CMAKE_CURRENT_BINARY_DIR}/cobra-3.6/src/cobra-3.6/bin_linux/cobra
  DESTINATION bin)

install(DIRECTORY 
  ${CMAKE_CURRENT_BINARY_DIR}/cobra-3.6/src/cobra-3.6/rules
  DESTINATION share/${PROJECT_NAME}
)

ament_environment_hooks(env_hook/cobra_vendor_base.dsv.in)

ament_package()
