
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


def find_blocks(src, start=0, nesting=0, scope=None):
    if not scope:
        scope = []
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
            if event.strip():
                if event == '{':
                    if accumulate:
                        scope.append(accumulate)
                        accumulate = ''
                    seek, new_scope = find_blocks(
                        src, seek, nesting+1, [text + event])
                    scope.append(new_scope)
                    continue
                    
                accumulate += text
                accumulate += event
                                        
                if event == '}':
                    if accumulate:
                        scope.append(accumulate)
                    if nesting != 0:
                        return seek, scope
                    else:
                        print "unexpected closing parenthesis"
            else:
                accumulate += text
                if event:
                    accumulate += event
        else:
            print "error parsing script, returning early"
            if accumulate:
                scope.append(accumulate)
            if nesting == 0:
                return scope
            else:
                return len(src), scope
    if accumulate:
        scope.append(accumulate)
    return scope


def find_immediates(src):
    """
    Return a flat list of tokens representing commands that could be
    executed immediately upon opening the level without any game
    state.  This includes anything that is not in a conditional block,
    and the contents of conditional blocks where the condition is only
    one of "playerenters" or "created".
    """
    blocks = find_blocks(src)
    found = []
    pattern = r'^\s*if\s*\(\s*(created|playerenters)\s*\)\s*{\s*$'
    for index, block in enumerate(blocks):
        if block and type(block) == list:
            first = block[0]
            if first and type(first) == unicode:
                first = first.encode("utf-8")
            if first and type(first) == str:
                if re.match(pattern, first, re.IGNORECASE):
                    found.append(block)
        if block and type(block) in [str, unicode]:
            found.append([block])

    reduced = []
    for block in found:
        tokens = [chunk for chunk in block if type(chunk) == str]
        flattened = '\n'.join(tokens)
        narrowed = re.match(
            r'(?:\A.*?{)(.*)(?:}.*?\Z)', flattened,
            re.MULTILINE | re.DOTALL)
        if narrowed:
            flattened = narrowed.groups()[0]
        commands = re.split(r'(?:\n|;)', flattened)
        reduced += [command.strip() for command in commands if
                    command.strip()]

    return reduced
