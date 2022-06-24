#!/usr/bin/env python3

# Copyright 2014-2015 Open Source Robotics Foundation, Inc.
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

import argparse
import glob
import json
import os
import re
from shutil import which
import subprocess
import sys


def get_cobra_version(cobra_bin):
    version_cmd = [cobra_bin, '-V']
    output = subprocess.check_output(version_cmd)
    # Expecting something like: b'Version 2.14 - 19 December 2016\n'
    output = output.decode().strip()
    tokens = output.split()
    if len(tokens) != 6:
        raise RuntimeError("unexpected cobra version string '{}'".format(output))
    return tokens[1]


def main(argv=sys.argv[1:]):
    extensions = ['c', 'cc', 'cpp', 'cxx']
    basic_args = ['-C++', '-comments', '-json']

    # The Cobra rulesets
    rulesets = ['basic', 'cwe', 'p10', 'jpl', 'misra2012', 'autosar']

    # Some rulesets may require additional arguments. There are currently no extra
    # arguments, but leave this here for now, to allow for convenient experiementation.
    associated_args = {
        'basic': [],
        'cwe': [],
        'p10': [],
        'jpl': [],
        'misra2012': [],
        'autosar': [],
    }

    # Define and parse the command-line options
    parser = argparse.ArgumentParser(
        description='Analyze source code using the cobra static analyzer.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        'paths',
        nargs='*',
        default=[os.curdir],
        help='Files and/or directories to be checked. Directories are searched recursively for '
             'files ending in one of %s.' %
             ', '.join(["'.%s'" % e for e in extensions]))
    parser.add_argument(
        '--include_dirs',
        nargs='*',
        help='Include directories for C/C++ files being checked.'
             "Each directory is passed to cobra as '-I<include_dir>'")
    parser.add_argument(
        '--exclude', default=[],
        nargs='*',
        help='Exclude C/C++ files from being checked.')
    parser.add_argument(
        '--ruleset',
        default='basic',
        help=f'The cobra rule set to use to analyze the code: {", ".join(rulesets)}.')
    parser.add_argument(
        '--compile_cmds',
        help='The compile_commands.json file from which to gather preprocessor directives. This '
        'option will take precedence over the --include_dirs options and any directories '
        'specified using --include_dirs will be ignored. Instead, ament_cobra will gather all '
        'preprocessor options from the compile_commands.json file.')
    parser.add_argument(
        '--xunit-file',
        help='Generate a xunit compliant XML file')
    parser.add_argument(
        '--sarif-file',
        help='Generate a SARIF file')
    parser.add_argument(
        '--cobra-version',
        action='store_true',
        help='Get the cobra version, print it, and then exit')
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Display verbose output')

    args = parser.parse_args(argv)

    target_binary = 'cobra' if args.ruleset != 'cwe' else 'cwe'
    cobra_bin = find_executable(target_binary)
    if not cobra_bin:
        print(f"Error: Could not find the '{target_binary}' executable", file=sys.stderr)
        return 1

    cobra_version = get_cobra_version(cobra_bin)
    if args.cobra_version:
        print(cobra_version)
        return 0

    groups = get_file_groups(args.paths, extensions, args.exclude)
    if not groups:
        print('No files found', file=sys.stderr)
        return 1

    cmd = [cobra_bin] + basic_args

    # If the user has provided a valid ruleset with --ruleset, add it
    if args.ruleset in rulesets:
        cmd.extend(['-f', args.ruleset if args.ruleset != 'autosar' else 'C++/autosar'])
        cmd.extend(associated_args[args.ruleset])
    else:
        print(f'Error: Invalid ruleset specified: {args.ruleset}', file=sys.stderr)
        return 1

    if args.compile_cmds and args.include_dirs:
        print('Warning: The include directories from the compile commands file will '
              'be used instead of the directories specified using --include_dirs')

    # Get the preprocessor options to use for each file from the
    # input compile_commands.json file
    options_map = {}
    if args.compile_cmds:
        f = open(args.compile_cmds)
        compile_data = json.load(f)

        for item in compile_data:
            compile_options = item['command'].split()

            # With some rulesets, preprocessor directives aren't required (and shouldn't
            # be provided or else Cobra will hang)
            preprocessor_options = []
            if args.ruleset not in ['basic', 'p10']:
                options = iter(compile_options)
                for option in options:
                    if option in ['-D', '-I', '-U']:
                        preprocessor_options.extend([option, options.__next__()])
                    elif option == '-isystem':
                        preprocessor_options.extend(['-I' + options.__next__()])
                    elif option.startswith(('-D', '-I', '-U')):
                        preprocessor_options.extend([option])

            options_map[item['file']] = {
                'directory': item['directory'],
                'options': preprocessor_options
            }

    error_count = 0

    # For each group of files
    for group_name in sorted(groups.keys()):
        files_in_group = groups[group_name]

        # If a compile_commands.json is provided, process each source file
        # separately, with its associated preprocessor directives
        if args.compile_cmds:
            for filename in files_in_group:
                if filename in options_map and options_map[filename]['options']:
                    arguments = cmd + options_map[filename]['options'] + [filename]
                else:
                    arguments = cmd + [filename]

                error_count += invoke_cobra(arguments, args.verbose)
        # Otherwise, run Cobra on this group of files
        else:
            arguments = cmd
            for include_dir in (args.include_dirs or []):
                cmd.extend(['-I' + include_dir])
            arguments.extend(files_in_group)
            error_count += invoke_cobra(arguments, args.verbose)

    # Output a summary
    if not error_count:
        print('No problems found')
        rc = 0
    else:
        print('%d errors' % error_count, file=sys.stderr)
        rc = 1

    # Unfortunately, the cwe and misra2012 rulesets are not outputting a JSON file
    # Issue submitted here: https://github.com/nimble-code/Cobra/issues/50
    ruleset_to_filename = {
        'basic': '_Basic_.txt',
        'cwe': None,  # No output JSON to work with (need #50 fixed)
        'p10': '_P10_.txt',
        'jpl': '_JPL_.txt',
        'misra2012': '_Misra2012_.txt',
        'autosar': '_Autosar_.txt',
    }

    input_filename = ruleset_to_filename[args.ruleset]

    if (args.xunit_file or args.sarif_file) and input_filename is None:
        print("Can't generate SARIF and/or JUnit XML output: "
              f"no input file for ruleset: {args.ruleset}", file=sys.stderr)
    else:
        # Generate the xunit output file
        if args.xunit_file:
            write_output_file(input_filename, '-junit', args.xunit_file)

        # Generate the SARIF output file
        if args.sarif_file:
            write_output_file(input_filename, '-sarif', args.sarif_file)

        # Remove the intermediate JSON results file (like '_Autosar_.txt')
        os.remove(input_filename)

    return rc


def find_executable(file_name, additional_paths=None):
    path = None
    if additional_paths:
        path = os.getenv('PATH', os.defpath)
        path += os.path.pathsep + os.path.pathsep.join(additional_paths)
    return which(file_name, path=path)


def invoke_cobra(arguments, verbose):
    """Invoke Cobra and log any issues."""
    try:
        if verbose:
            print(' '.join(arguments))
        p = subprocess.Popen(arguments, stdout=subprocess.PIPE)
        cmd_output = p.communicate()[0]
    except subprocess.CalledProcessError as e:
        print("The invocation of 'cobra' failed with error code %d: %s" %
              (e.returncode, e), file=sys.stderr)
        return 1

    lines = cmd_output.decode('utf-8').split('\n')
    total_errors = 0
    for line in lines:
        m = re.search('.*, ([0-9]+) patterns ::.*', line)
        if m is not None:
            total_errors += int(m.group(1))
        print(line)

    return total_errors


def get_files(paths, extensions):
    files = []
    for path in paths:
        if os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                if 'AMENT_IGNORE' in dirnames + filenames:
                    dirnames[:] = []
                    continue
                # ignore folder starting with . or _
                dirnames[:] = [d for d in dirnames if d[0] not in ['.', '_']]
                dirnames.sort()

                # select files by extension
                for filename in sorted(filenames):
                    _, ext = os.path.splitext(filename)
                    ext_list = ['.%s' % e for e in extensions]
                    if ext in ext_list:
                        files.append(os.path.join(dirpath, filename))
        if os.path.isfile(path):
            files.append(path)
    return [os.path.normpath(f) for f in files]


def get_file_groups(paths, extensions, exclude_patterns):
    excludes = []
    for exclude_pattern in exclude_patterns:
        excludes.extend(glob.glob(exclude_pattern))
    excludes = {os.path.realpath(x) for x in excludes}

    # dict mapping root path to files
    groups = {}
    for path in paths:
        if os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                if 'AMENT_IGNORE' in dirnames + filenames:
                    dirnames[:] = []
                    continue
                # ignore folder starting with . or _
                dirnames[:] = [d for d in dirnames if d[0] not in ['.', '_']]
                dirnames.sort()

                # select files by extension
                for filename in sorted(filenames):
                    _, ext = os.path.splitext(filename)
                    if ext in ('.%s' % e for e in extensions):
                        filepath = os.path.join(dirpath, filename)
                        if os.path.realpath(filepath) not in excludes:
                            append_file_to_group(groups, filepath)

        if os.path.isfile(path):
            if os.path.realpath(path) not in excludes:
                append_file_to_group(groups, path)

    return groups


def append_file_to_group(groups, path):
    path = os.path.abspath(path)

    root = ''

    # try to determine root from path
    base_path = os.path.dirname(path)
    # find longest subpath which ends with one of the following subfolder names
    subfolder_names = ['include', 'src', 'test']
    matches = [
        re.search(
            '^(.+%s%s)%s' %
            (re.escape(os.sep), re.escape(subfolder_name), re.escape(os.sep)), path)
        for subfolder_name in subfolder_names]
    match_groups = [match.group(1) for match in matches if match]
    if match_groups:
        match_groups = [{'group_len': len(x), 'group': x} for x in match_groups]
        sorted_groups = sorted(match_groups, key=lambda k: k['group_len'])
        base_path = sorted_groups[-1]['group']
        root = base_path

    # try to find repository root
    repo_root = None
    p = path
    while p and repo_root is None:
        # abort if root is reached
        if os.path.dirname(p) == p:
            break
        p = os.path.dirname(p)
        for marker in ['.git', '.hg', '.svn']:
            if os.path.exists(os.path.join(p, marker)):
                repo_root = p
                break

    # compute relative --root argument
    if repo_root and repo_root > base_path:
        root = os.path.relpath(base_path, repo_root)

    # add the path to the appropriate group
    if root not in groups:
        groups[root] = []
    groups[root].append(path)


def write_output_file(input_filename, conversion_flag, output_filename):
    folder_name = os.path.basename(os.path.dirname(output_filename))
    try:
        cmd = ['json_convert', conversion_flag, '-f', os.path.join(folder_name, input_filename)]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        cmd_output = p.communicate()[0]
        with open(output_filename, 'w') as f:
            f.write(cmd_output.decode("utf-8"))
    except subprocess.CalledProcessError as e:
        print(f"'json_convert' failed with error code {e.returncode}: {e}", file=sys.stderr)


if __name__ == '__main__':
    sys.exit(main())
