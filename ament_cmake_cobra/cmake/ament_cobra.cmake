# Copyright 2021 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# Add a test to perform static code analysis with cobra.
#
# The include dirs for cobra to consider can either be set by the function
# parameter 'INCLUDE_DIRS` or by a global variable called
# 'ament_cmake_cobra_ADDITIONAL_INCLUDE_DIRS'.
#
# :param TESTNAME: the name of the test, default: "cobra"
# :type TESTNAME: string
# :param RULESET: the rule set to use (basic, cwe, p10, jpl, or misra2012)
# :type RULESET: string
# :param INCLUDE_DIRS: an optional list of include paths for cobra
# :type INCLUDE_DIRS: list
# :param EXCLUDE: an optional list of exclude directories or files for cpplint
# :type EXCLUDE: list
# :param COMPILE_CMDS: Full path to the compile_commands.json file
# :type COMPILE_CMDS: string
# :param EXCLUDE: an optional list of exclude directories or files for cpplint
# :type EXCLUDE: list
# :param ARGN: the files or directories to check
# :type ARGN: list of strings
#
# @public
#
function(ament_cobra)
  cmake_parse_arguments(ARG "" "EXCLUDE;RULESET;TESTNAME;COMPILE_CMDS" "INCLUDE_DIRS" ${ARGN})
  if(NOT ARG_TESTNAME)
    set(ARG_TESTNAME "cobra")
  endif()

  find_program(ament_cobra_BIN NAMES "ament_cobra")
  if(NOT ament_cobra_BIN)
    message(FATAL_ERROR "ament_cobra() could not find program 'ament_cobra'")
  endif()

  set(xunit_result_file "${AMENT_TEST_RESULTS_DIR}/${PROJECT_NAME}/${ARG_TESTNAME}.xunit.xml")
  set(sarif_result_file "${AMENT_TEST_RESULTS_DIR}/${PROJECT_NAME}/${ARG_TESTNAME}.sarif")
  set(cmd "${ament_cobra_BIN}" "--xunit-file" "${xunit_result_file}" "--sarif-file" "${sarif_result_file}")
  list(APPEND cmd ${ARG_UNPARSED_ARGUMENTS})

  if(ARG_RULESET)
    list(APPEND cmd "--ruleset" "${ARG_RULESET}")
  endif()
  if(ARG_INCLUDE_DIRS)
    list(APPEND cmd "--include_dirs" "${ARG_INCLUDE_DIRS}")
  endif()
  if(ARG_EXCLUDE)
    list(APPEND cmd "--exclude" "${ARG_EXCLUDE}")
  endif()
  if(ARG_COMPILE_CMDS)
    list(APPEND cmd "--compile_cmds" "${ARG_COMPILE_CMDS}")
  endif()

  file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/ament_cobra")
  ament_add_test(
    "${ARG_TESTNAME}"
    COMMAND ${cmd}
    TIMEOUT 302
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/ament_cobra/${ARG_TESTNAME}.txt"
    RESULT_FILE "${xunit_result_file}"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  )
  set_tests_properties(
    "${ARG_TESTNAME}"
    PROPERTIES
    LABELS "cobra;linter"
  )
endfunction()
