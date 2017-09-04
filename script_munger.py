
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


import re


def find_blocks(src, start=0, nesting=0, scope=[]):
    seek = start;
    accumulate = ''
    while seek < (len(src)):
        chunk = re.match(
            r'^(.*?)({|}|\n|\Z|//.*?\n\Z|//\*.*?\*//)',
            src[seek:], re.MULTILINE | re.DOTALL)
        if chunk:
            seek += (chunk.end() - chunk.start())
            text, event = chunk.groups()
            assert(text.count("}") == 0)
            if event:
                if event == '{':
                    if accumulate:
                        scope.append(accumulate)
                        accumulate = ''
                    seek, new_scope = find_blocks(
                        src, seek, nesting+1, [text + event])
                    scope.append(new_scope)
                    continue
                    
                accumulate += text
                if event:
                    accumulate += event
                                        
                if event == '}':
                    scope.append(accumulate)
                    if nesting != 0:
                        return seek, scope
                    else:
                        print "unexpected closing parenthesis"
        else:
            print "error parsing script, returning early"
            if nesting == 0:
                return scope
            else:
                return len(src), scope
    return scope


def find_init_commands(src):
    blocks = find_blocks(src)
    found = None
    for index, block in enumerate(blocks):
        if block and type(block) == list:
            first = block[0]
            if first and type(first) == unicode:
                first = first.encode("utf-8")
            if first and type(first) == str:
                if re.match(r'^\s*if\s*\(\s*playerenters\s*\)\s*{\s*$',
                            first):
                    found = block
                    break

    reduced = [chunk for chunk in found if type(chunk) == str]
    flattened = '\n'.join(reduced)
    narrowed = re.match(
        r'(?:\A.*?{)(.*)(?:}.*?\Z)', flattened,
        re.MULTILINE | re.DOTALL).groups()[0]

    commands = re.split(r'(?:\n|;)', narrowed)
    reduced = [command.strip() for command in commands if command.strip()]
    return reduced
