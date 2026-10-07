# MIT License
#
# Copyright (c) 2017 Dan Persons <dpersonsdev@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Streaming CLI for the logdissect output layer.

The --format json/csv branches below call logdissect.output.json_output
and logdissect.output.csv_output with the shared FIELD_TABLE, so CLI
output is byte-identical to direct library calls.
"""

import os
import sys
from argparse import ArgumentParser

from logdissect.output import FIELD_TABLE, SPILL_WINDOW
from logdissect.output import json_output, csv_output


def build_arg_parser():
    """Build the command line argument parser"""
    arg_parser = ArgumentParser(prog='logdissect',
            description='parse logs and stream them as JSON or CSV')
    arg_parser.add_argument('--format', action='store', dest='format',
            choices=('json', 'csv'), default='json',
            help='output format (default: json)')
    arg_parser.add_argument('-o', '--output', action='store', dest='output',
            default=None,
            help='output file (default: standard output)')
    arg_parser.add_argument('--sort', action='store_true', dest='sort',
            help='sort all entries by UTC timestamp '
            '(bounded-window external sort)')
    arg_parser.add_argument('--window', action='store', dest='window',
            type=int, default=SPILL_WINDOW,
            help='sort window size in entries (default: %(default)s)')
    arg_parser.add_argument('-p', '--parser', action='store', dest='parser',
            default='syslog',
            help='select a parser (default: syslog)')
    arg_parser.add_argument('-t', '--tzone', action='store', dest='tzone',
            default=None,
            help='timezone of the input, as +-HHMM offset or '
            'IANA zone name (e.g. America/New_York); '
            'default: system local zone, resolved per entry')
    arg_parser.add_argument('files', metavar='file', nargs='+',
            help='specify input files')
    return arg_parser


def load_entries(files, parser_name='syslog', tzone=None):
    """Parse input files and return their entries in file order"""
    parse_module = __import__('logdissect.parsers.' + parser_name,
            globals(), locals(), ['logdissect']).ParseModule()
    if tzone:
        parse_module.tzone = tzone
    entries = []
    for path in files:
        data = parse_module.parse_file(os.path.abspath(path))
        entries.extend(data['entries'])
    return entries


def main(argv=None):
    """Run the streaming CLI"""
    args = build_arg_parser().parse_args(argv)
    entries = load_entries(args.files, parser_name=args.parser,
            tzone=args.tzone)
    if args.format == 'json':
        json_output(entries, args.output, fields=FIELD_TABLE,
                sort=args.sort, window=args.window)
    elif args.format == 'csv':
        csv_output(entries, args.output, fields=FIELD_TABLE,
                sort=args.sort, window=args.window)
    return 0


if __name__ == '__main__':
    sys.exit(main())
