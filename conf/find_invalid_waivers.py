#!/usr/bin/python3
"""
This is a standalone script which processes provided results.txt.gz files
and identifies invalid waivers. The waiver is invalid if it:
 - did not match any test results,
 - or only matched the 'pass' test results.

The identified invalid waivers are printed to the standard output.
"""

import re
import sys
import gzip
import pathlib
import argparse
import textwrap

# add the parent directory to the sys.path so we can import from the lib directory
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))
from lib import waive, versions

_sections_cache = None


def find_regexes_in_list(regexes_matched_list, regexes):
    for index, (list_regexes, _) in enumerate(regexes_matched_list):
        if list_regexes == regexes:
            return index
    return None


def add_regexes_to_list(regexes_matched_list, regexes, non_pass_result):
    index = find_regexes_in_list(regexes_matched_list, regexes)
    if index is not None:
        # tuple with the regexes is already in the list, the boolean value
        # needs to be modified only in case we matched a non-pass test result
        # and it is not already marked as such in the existing tuple
        if non_pass_result is True and regexes_matched_list[index][1] is False:
            regexes_matched_list[index] = (regexes_matched_list[index][0], non_pass_result)
    else:
        # tuple with the regexes not found, add it to the list
        regexes_matched_list.append((regexes, non_pass_result))


def unwaive_note(waive_text, note):
    return note.lstrip(waive_text).rstrip(')')


def match_result_mark_waiver(regexes_matched_list, version, arch, status, name, note):
    """This function is an updated version of the match_result() function from the lib/waive.py."""
    version = versions._Rhel(version=version, id='rhel')

    # make sure "'something' in name" always works
    if name is None:
        name = ''
    if note is None or note == '[]':
        note = ''

    if '(waived pass)' in note:
        note = unwaive_note('(waived pass)', note)
    elif '(waived fail)' in note:
        note = unwaive_note('(waived fail)', note)
        status = 'fail'
    elif '(waived error)' in note:
        note = unwaive_note('(waived error)', note)
        status = 'error'

    objs = {
        'status': status,
        'name': name,
        'note': note,
        'arch': arch,
        'rhel': version,
        'oscap': '',
        'env': '',
        'Match': waive.Match,
    }

    for section in _sections_cache:
        if any(x.fullmatch(name) for x in section.regexes):
            ret = eval(section.python_code, objs, None)

            if not isinstance(ret, waive.Match):
                if not isinstance(ret, bool):
                    raise RuntimeError(f"waiver python code did not return bool or Match: {ret}")
                ret = waive.Match(ret)

            if ret:  # both regex and python code matched
                add_regexes_to_list(regexes_matched_list, section.regexes, bool(status != 'pass'))


def load_and_process_results(file, regexes_matched_list):
    with gzip.open(file, 'rt') as f:
        for line in f:
            line = line.strip()
            version, arch, status, name, note = line.split('\t')

            if status not in ['pass', 'fail', 'error', 'warn']:
                continue

            match_result_mark_waiver(regexes_matched_list, version, arch, status, name, note)


def main(result_file_list):
    regexes_matched_list = []
    """
    [
        # list of tuples containing regexes matching some test result and a Boolean value
        # set to True if regexes matched any non-pass test result, otherwise False
        (set(regexes), True/False),
        (set(regexes), True/False),
        ...
    ]
    """
    global _sections_cache
    _sections_cache = list(waive.collect_waivers())

    for file in result_file_list:
        load_and_process_results(file, regexes_matched_list)

    print("===============================================================\n"
          "The following waivers are no longer valid, they either did not\n"
          "match any test results or only matched the 'pass' test results:\n"
          "===============================================================\n")
    for section in _sections_cache:
        index = find_regexes_in_list(regexes_matched_list, section.regexes)
        # if the section did not match any test results or only matched the 'pass' test results:
        if index is None or regexes_matched_list[index][1] is False:
            python_source = next(
                (i.python_source for i in _sections_cache if i.regexes == section.regexes),
                None,
            )
            # if "is_centos()" is in python_src_code variable and there is no "or"
            # logical operator the section is only applicable for centos so skip it
            or_operator_in_py_code = bool(re.search(r'\s+or\s+', python_source) is not None)
            centos_section = bool('is_centos()' in python_source and not or_operator_in_py_code)
            if not centos_section:
                for regex in section.regexes:
                    print(regex.pattern)
                print(f"    {python_source}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=textwrap.dedent("""
        Process results.txt.gz files and identify invalid waivers.
        The waiver is invalid if it did not match any test results
        or only matched the 'pass' test results.

        IMPORTANT: Test results for all RHEL versions need to be
        provided, otherwise this script won't be able to identify
        the invalid waivers properly.
        """),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "result_file", nargs='+',
        help="The results.txt.gz file with test results to process",
    )
    args = parser.parse_args()
    main(args.result_file)
