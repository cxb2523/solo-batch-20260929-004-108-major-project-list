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

import re
import time
from time import localtime
from time import timezone
from time import altzone
from datetime import datetime, timedelta

def convert_standard_datestamp(entry):
    """Set date and time attributes based on a standard date stamp"""
    # Get the date stamp (without year)
    months = {'Jan': '01', 'Feb': '02', 'Mar': '03',
            'Apr': '04', 'May': '05', 'Jun': '06',
            'Jul': '07', 'Aug': '08', 'Sep': '09',
            'Oct': '10', 'Nov': '11', 'Dec': '12'}
    datelist = entry['date_stamp'].split(' ')
    try:
        datelist.remove('')
    except ValueError:
        pass
    intmonth = months[datelist[0].strip()]
    daydate = datelist[1].strip().zfill(2)
    timestring = datelist[2].replace(':','')
    datestampnoyear = intmonth + daydate + timestring

    # Set attributes:
    entry['year'] = None
    entry['month'] = intmonth
    entry['day'] = daydate
    entry['tstamp'] = timestring
    entry['tzone'] = None

    return entry


def convert_nodate_datestamp(entry, datedata):
    """Set date and time attributes based on timestamp with no date"""
    entry['tstamp'] = entry['date_stamp'].replace(':', '')
    # Remember, we're parsing in reverse.
    if '.' in entry['tstamp']:
        tstamp = entry['tstamp'].split('.')[0]
    else:
        tstamp = entry['tstamp']
    if int(tstamp) > datedata['entry_time']:
        datedata['timestamp'] = datedata['timestamp'] - timedelta(days=1)
    if '.' in entry['tstamp']:
        datedata['entry_time'] = int(entry['tstamp'].split('.')[0])
    else:
        datedata['entry_time'] = int(entry['tstamp'])
    entry['year'] = str(datedata['timestamp'].year)
    entry['month'] = str(datedata['timestamp'].month.rjust(2, '0'))
    entry['day'] = str(datedata['timestamp'].day).rjust(2, '0')
    entry['numeric_date_stamp'] = entry['year'] + entry['month'] + \
            entry['day'] + entry['tstamp']
    entry['tzone'] = None

    return entry, datedata


def convert_iso_datestamp(entry):
    """Set date and time attributes based on an iso date stamp"""
    # Set our attributes:
    if entry['date_stamp'][-1] == 'Z':
        tzone = '+0000'
        datestamp = entry['date_stamp'][:-1].strip('-').strip('T').strip(':')
    else:
        tzone = entry['date_stamp'][-5:].strip(':')
        datestamp = entry['date_stamp'][:-6].strip('-').strip('T').strip(':')

    entry['year'] = datestamp[0:4]
    entry['month'] = datestamp[4:6]
    entry['day'] = datestamp[6:8]
    entry['tstamp'] = datestamp[8:]
    entry['tzone'] = tzone
    entry['numeric_date_stamp'] = entry['year'] + entry['month'] + \
            entry['day'] + entry['tstamp']

    return entry


def convert_webaccess_datestamp(entry):
    """Set date and time attributes based on an iso date stamp"""
    attrlist = entry['date_stamp'].split('/')
    timelist = attrlist[-1].split(':')
    entry['year'] = timelist[0]
    months = {'Jan': '01', 'Feb': '02', 'Mar': '03',
            'Apr': '04', 'May': '05', 'Jun': '06',
            'Jul': '07', 'Aug': '08', 'Sep': '09',
            'Oct': '10', 'Nov': '11', 'Dec': '12'}
    entry['month'] = months[attrlist[1]]
    entry['day'] = attrlist[0]
    entry['tstamp'] = ''.join(timelist[1:])
    entry['numeric_date_stamp'] = entry['year'] + entry['month'] + \
            entry['day'] + entry['tstamp']

    return entry


def convert_unix_datestamp(entry):
    """Set date and time attributes based on a unix date stamp"""
    timestamp = datetime.fromtimestamp(float(entry['date_stamp']))
    entry['year'] = str(timestamp.year)
    entry['month'] = str(timestamp.month).rjust(2, '0')
    entry['day'] = str(timestamp.day).rjust(2, '0')
    entry['tstamp'] = str(timestamp.strftime('%H%M%S.%f'))
    entry['numeric_date_stamp'] = entry['year'] + entry['month'] + \
            entry['day'] + entry['tstamp']

    return entry


def convert_now_datestamp(entry):
    """Set date and time attributes based on a unix date stamp"""
    timestamp = datetime.now()
    entry['date_stamp'] = timestamp.strftime('%Y %b %d %H:%M:%S.%f')
    entry['year'] = str(timestamp.year)
    entry['month'] = str(timestamp.month).rjust(2, '0')
    entry['day'] = str(timestamp.day).rjust(2, '0')
    entry['tstamp'] = timestamp.strftime('%H%M%S.%f')
    entry['numeric_date_stamp'] = entry['year'] + entry['month'] + \
            entry['day'] + entry['tstamp']

    return entry


def _parse_numeric_stamp(stamp):
    """Parse a numeric date stamp into a naive datetime"""
    if '.' in stamp:
        return datetime.strptime(stamp, '%Y%m%d%H%M%S.%f')
    return datetime.strptime(stamp, '%Y%m%d%H%M%S')


def _format_utc_offset(offset):
    """Format a timedelta UTC offset as +-HHMM"""
    total = int(offset.total_seconds())
    sign = '+' if total >= 0 else '-'
    total = abs(total)
    return '%s%02d%02d' % (sign, total // 3600, (total % 3600) // 60)


def _fixed_offset(tzone):
    """Parse a +-HHMM offset string into a timedelta, or return None"""
    if not tzone:
        return None
    match = re.match(r'^([+-])(\d{2}):?(\d{2})$', str(tzone))
    if not match:
        return None
    delta = timedelta(hours=int(match.group(2)),
            minutes=int(match.group(3)))
    if match.group(1) == '-':
        delta = -delta
    return delta


def _named_zone_offset(t, zonename):
    """UTC offset for a naive local datetime in an IANA time zone"""
    from zoneinfo import ZoneInfo
    zone = ZoneInfo(zonename)
    return t.replace(tzinfo=zone).utcoffset()


def _local_zone_offset(t):
    """UTC offset of the system local zone at a naive datetime (DST-aware)"""
    try:
        epoch = time.mktime((t.year, t.month, t.day, t.hour, t.minute,
                t.second, 0, 0, -1))
        utc_t = datetime.utcfromtimestamp(epoch)
        return t.replace(microsecond=0) - utc_t.replace(microsecond=0)
    except (OverflowError, OSError, ValueError):
        return None


def resolve_utc_offset(t, tzone=None):
    """Resolve the UTC offset for a naive local datetime.

    Resolution order: an explicit +-HHMM offset, an IANA zone name
    (DST-aware per entry), the system local zone at that datetime
    (DST-aware per entry), and finally the current system offset.
    """
    offset = _fixed_offset(tzone)
    if offset is not None:
        return offset
    if tzone:
        try:
            return _named_zone_offset(t, tzone)
        except Exception:
            pass
    offset = _local_zone_offset(t)
    if offset is not None:
        return offset
    return _fixed_offset(get_local_tzone())


def get_utc_date(entry):
    """Return datestamp converted to UTC"""
    if entry['numeric_date_stamp'] == '0':
        entry['numeric_date_stamp_utc'] = '0'
        return entry

    else:
        t = _parse_numeric_stamp(entry['numeric_date_stamp'])
        offset = resolve_utc_offset(t, entry.get('tzone'))

        # Keep the entry's own local offset for the presentation layer:
        entry['tzone'] = _format_utc_offset(offset)
        ut = t - offset

        entry['numeric_date_stamp_utc'] = ut.strftime('%Y%m%d%H%M%S.%f')

        return entry


def get_local_tzone():
    """Get the current time zone on the local host"""
    if localtime().tm_isdst:
        if altzone < 0:
            tzone = '+' + \
                    str(int(float(altzone) / 60 // 60)).rjust(2,
                            '0') + \
                            str(int(float(
                                altzone) / 60 % 60)).ljust(2, '0')
        else:
            tzone = '-' + \
                    str(int(float(altzone) / 60 // 60)).rjust(2,
                            '0') + \
                            str(int(float(
                                altzone) / 60 % 60)).ljust(2, '0')
    else:
        if altzone < 0:
            tzone = \
                    '+' + str(int(float(timezone) / 60 // 60)).rjust(2,
                            '0') + \
                            str(int(float(
                                timezone) / 60 % 60)).ljust(2, '0')
        else:
            tzone = \
                    '-' + str(int(float(timezone) / 60 // 60)).rjust(2,
                            '0') + \
                            str(int(float(
                                timezone) / 60 % 60)).ljust(2, '0')

    return tzone


def merge_logs(dataset, sort=True):
    """Merge log dictionaries together into one log dictionary"""
    ourlog = {}
    ourlog['entries'] = []
    for d in dataset:
        ourlog['entries'] = ourlog['entries'] + d['entries']
    if sort:
        ourlog['entries'].sort(key= lambda x: x['numeric_date_stamp_utc'])

    return ourlog
