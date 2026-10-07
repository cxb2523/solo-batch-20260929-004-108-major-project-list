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

__formats__ = ['log', 'linejson', 'sojson']

import logdissect.output.log
import logdissect.output.linejson
import logdissect.output.sojson

import contextlib
import csv
import heapq
import json
import os
import sys
import tempfile

from logdissect.output.fields import FIELD_TABLE, project_entry

# Maximum number of entries held in memory per sort window; larger
# inputs spill to temporary files and are merged back with a heap.
SPILL_WINDOW = 1000


def entry(raw_entry, fields=FIELD_TABLE):
    """Project one raw entry onto the canonical field table"""
    return project_entry(raw_entry, fields)


def _sort_key(projected):
    stamp = projected.get('timestamp_utc')
    return (stamp is None, stamp or '')


def _spill(chunk, tempdir=None):
    """Write one sorted chunk to a temporary spill file"""
    chunk.sort(key=_sort_key)
    fd, path = tempfile.mkstemp(prefix='.logdissect-spill-',
            suffix='.tmp', dir=tempdir)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
        for projected in chunk:
            handle.write(json.dumps(projected, sort_keys=True,
                    ensure_ascii=False) + '\n')
    return path


def _iter_spill(path):
    with open(path, 'r', encoding='utf-8', newline='') as handle:
        for line in handle:
            line = line.rstrip('\n')
            if line:
                yield json.loads(line)


def iter_sorted(entries, fields=FIELD_TABLE, window=SPILL_WINDOW,
        tempdir=None):
    """Yield projected entries in total timestamp order.

    Uses a bounded-window external sort: chunks of at most ``window``
    entries are sorted in memory and spilled to temporary files, then
    k-way merged. Spill files are always removed, even on interruption.
    """
    buffer = []
    spills = []
    try:
        for raw_entry in entries:
            buffer.append(project_entry(raw_entry, fields))
            if len(buffer) >= window:
                spills.append(_spill(buffer, tempdir))
                buffer = []
        if not spills:
            for projected in sorted(buffer, key=_sort_key):
                yield projected
            return
        if buffer:
            spills.append(_spill(buffer, tempdir))
        streams = [_iter_spill(path) for path in spills]
        for projected in heapq.merge(*streams, key=_sort_key):
            yield projected
    finally:
        for path in spills:
            try:
                os.unlink(path)
            except OSError:
                pass


def _projected_stream(entries, fields, sort, window):
    if sort:
        return iter_sorted(entries, fields=fields, window=window)
    return (project_entry(raw_entry, fields) for raw_entry in entries)


@contextlib.contextmanager
def _open_dest(dest, newline=''):
    """Open the destination, streaming to a temp file first.

    File destinations are written to a temporary file in the same
    directory and atomically moved into place, so an interrupted run
    never leaves a partial product behind.
    """
    if dest is None:
        yield sys.stdout
        return
    if hasattr(dest, 'write'):
        yield dest
        return
    path = os.fspath(dest)
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmppath = tempfile.mkstemp(prefix='.logdissect-out-',
            suffix='.tmp', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline=newline) as handle:
            yield handle
        os.replace(tmppath, path)
    except BaseException:
        try:
            os.unlink(tmppath)
        except OSError:
            pass
        raise


def _dump_json_line(projected):
    return json.dumps(projected, sort_keys=True, ensure_ascii=False)


def json_output(entries, dest=None, fields=FIELD_TABLE, sort=False,
        window=SPILL_WINDOW):
    """Write entries as JSON lines (one projected object per line).

    Streaming by default; with sort=True a bounded-window external
    sort through temporary files guarantees total order.
    """
    with _open_dest(dest) as handle:
        with contextlib.closing(_projected_stream(
                entries, fields, sort, window)) as stream:
            for projected in stream:
                handle.write(_dump_json_line(projected) + '\n')


def csv_output(entries, dest=None, fields=FIELD_TABLE, sort=False,
        window=SPILL_WINDOW):
    """Write entries as CSV with the field table as the leading columns.

    Undeclared fields are appended as extra columns in sorted order;
    missing values serialize as empty cells, keys are never dropped.
    """
    if not hasattr(entries, '__len__'):
        entries = list(entries)
    declared = set(fields)
    extras = sorted({key for raw_entry in entries
            for key in raw_entry if key not in declared})
    header = list(fields) + extras
    with _open_dest(dest, newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=header,
                lineterminator='\n', extrasaction='ignore')
        writer.writeheader()
        with contextlib.closing(_projected_stream(
                entries, fields, sort, window)) as stream:
            for projected in stream:
                writer.writerow(projected)
