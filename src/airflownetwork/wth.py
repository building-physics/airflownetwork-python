# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import pandas
import datetime
import io

class BadDate(Exception):
    pass

def get_date(string):
    parts = string.split('/')
    if len(parts) != 2:
        raise BadDate('Wrong number of parts in the date')
    return int(parts[0]), int(parts[1])

class WthData:
    def __init__(self, description, start_month, start_day, df, year=2006):
        self.description = description
        self.start = datetime.datetime(year=year, month=start_month, day=start_day)
        self.df = df
    @classmethod
    def from_wth(cls, fp, year=2006):
        lines = []
        for line in fp:
            line = line.strip()
            if not line.startswith('!'):
                lines.append(line)
        try:
            lines.pop(0) # Discard the program and version info
            description = lines.pop(0) # Keep the description
            start_date_string = lines.pop(0).partition('!')
            end_date_string = lines.pop(0).partition('!')
            start_month, start_day = get_date(start_date_string)
            end_month, end_day = get_date(end_date_string)
        except (IndexError, BadDate):
            return None
        
        start = datetime.datetime(year=year, month=start_month, day=start_day)
        end = datetime.datetime(year=year, month=end_month, day=end_day)

