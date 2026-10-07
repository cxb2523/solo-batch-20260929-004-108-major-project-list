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

"""Single canonical field table for the logdissect output layer.

Both logdissect.output (entry/json_output/csv_output) and logdissect.cli
import this table; it must never be copied into call sites.

Projection rules (subtraction only):
- declared fields appear in table order; a missing value becomes None
  (JSON null / empty CSV cell) and the key is never omitted;
- fields not declared here pass through untouched, in their original
  order, after the declared fields.
"""

FIELD_TABLE = (
        'timestamp_utc',
        'year',
        'month',
        'day',
        'tstamp',
        'tzone',
        'log_source',
        'source_process',
        'source_pid',
        'message',
        'parser',
        'source_path',
        'raw_text',
        )


def iso8601_utc(numeric_date_stamp_utc):
    """Serialize a numeric UTC stamp as ISO8601 UTC with milliseconds.

    '20260308065959.123456' -> '2026-03-08T06:59:59.123Z'
    Returns None for missing or zero stamps.
    """
    if not numeric_date_stamp_utc or numeric_date_stamp_utc == '0':
        return None
    stamp = str(numeric_date_stamp_utc)
    if '.' in stamp:
        main, frac = stamp.split('.', 1)
    else:
        main, frac = stamp, ''
    if len(main) != 14 or not main.isdigit():
        return None
    millis = (frac + '000')[:3]
    return '%s-%s-%sT%s:%s:%s.%sZ' % (
            main[0:4], main[4:6], main[6:8],
            main[8:10], main[10:12], main[12:14], millis)


def project_entry(raw_entry, fields=FIELD_TABLE):
    """Project a raw entry onto the field table (subtraction only).

    Declared fields come first in table order, missing ones as None;
    undeclared fields are preserved as-is after the declared ones.
    """
    projected = {}
    for name in fields:
        if name == 'timestamp_utc':
            projected[name] = iso8601_utc(
                    raw_entry.get('numeric_date_stamp_utc'))
        else:
            projected[name] = raw_entry.get(name)
    declared = set(fields)
    for key, value in raw_entry.items():
        if key not in declared:
            projected[key] = value
    return projected
