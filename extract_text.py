#!/usr/bin/env python

#  Copyright (c) 2017, Aeva M. Palecek

#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import glob
import json
from util import extract_text
from parser_common import UnknownFileHeader


if __name__ == "__main__":
    paths = []
    def ingest(path):
        if os.path.isdir(path):
            for dirpath, dir_names, file_names in os.walk(path):
                for file_name in file_names:
                    path = os.path.join(dirpath, file_name)
                    paths.append(path)
            
        if os.path.isfile(path):
            paths.append(path)

    mode = "JSON"
    for arg in sys.argv[1:]:
        if arg == "--markdown":
            mode = "MD"
            continue
        map(ingest, glob.glob(arg))

    data = []
    for level_path in paths:
        try:
            level_text = extract_text(level_path)
        except UnknownFileHeader:
            continue
        if level_text:
            data.append({
                "level" : os.path.split(level_path)[-1],
                "text" : map(lambda x: x.encode("utf-8"), level_text),
            })

    if mode == "JSON":
        print json.dumps(data, ensure_ascii=False)

    elif mode == "MD":
        markdown = u''
        for packet in data:
            level = packet["level"]
            signs = packet["text"]
            markdown += u"\n# {}\n".format(level.encode("utf-8"))
            for sign_index, sign in enumerate(signs):
                sign = sign.decode("utf-8")
                markdown += u"#### block {}\n".format(sign_index)
                lines = sign.split(u"\n")
                for line_index, line in enumerate(lines):
                    page_start = line_index % 3 == 0
                    page_end = line_index % 3 == 2
                    terminus = line_index == len(lines)-1
                    
                    if page_start:
                        markdown += u"> ```\n"
                    markdown += u"> {}\n".format(line)
                    
                    if page_end or terminus:
                        markdown += u"> ```\n\n"
        
        print markdown.encode("utf-8")
