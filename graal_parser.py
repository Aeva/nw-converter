
#  Copyright (c) 2016, Aeva M. Palecek

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
import re
import sys
import math
import struct

from parser_common import LevelParser, GLYPHS


REVISIONS = ("Z3-V1.00", # <- untested
             "Z3-V1.01", # <- untested
             "Z3-V1.02", # <- untested
             "Z3-V1.03",
             "Z3-V1.04",
             "GR-V1.00",
             "GR-V1.01",
             "GR-V1.02",
             "GR-V1.03")


Z3_0 = 0
Z3_1 = 1
Z3_2 = 2
Z3_3 = 3
Z3_4 = 4
GR_0 = 5
GR_1 = 6
GR_2 = 7
GR_3 = 8


GLYPHS = string.uppercase + string.lowercase + string.digits
GLYPHS = GLYPHS.encode("utf-8")
GLYPHS += u"!?-.,"
GLYPHS += u"\u2026" # ellipsis
GLYPHS += u">()"
GLYPHS += u"\u2c0f" # glagolitic symbol
GLYPHS += u"\u2c29" # glagolitic symbol
GLYPHS += u"\u2c27" # glagolitic symbol
GLYPHS += u'\u200B' # padding
GLYPHS += u"\U0001F467" # person
GLYPHS += u'"'
GLYPHS += u"\U0001f839" # up
GLYPHS += u"\U0001f83b" # down
GLYPHS += u"\U0001f838" # left
GLYPHS += u"\U0001f83a" # right
GLYPHS += u"':/~&#"
GLYPHS += u'\u200B' # padding, control code
GLYPHS += u"\U0001F497" # heart
GLYPHS += u" <"
GLYPHS += u"\u24b6" # circle A
GLYPHS += u"\u24b7" # circle B
GLYPHS += u"\u24cd" # circle X
GLYPHS += u"\u24ce" # circle Y
GLYPHS += u";"
GLYPHS += u"\n"


class DotGraalParser(LevelParser):
    """
    This class takes a path to a .graal encoded file, decodes it, and
    provides a means of easily accessing the contained data.
    """

    def file_version(self):
        assert(self.header in REVISIONS)
        return REVISIONS.index(self.header)

    
    def parse(self):
        assert(self.version >= Z3_3)
        raw = open(self._uri, "r").read()

        # we start at 8 to seek just after the file header
        offset = 8
        bits_read = 0

        # tile data is packed in intervals of 12 or 13 bits
        packet_size = 13 if self.version >= GR_2 else 12
        
        packet_mask = (2**packet_size)-1
        repeat_mask = 2**(packet_size-1)
        double_mask = 0x100
        count_mask = 0xFF
        tile_mask = packet_mask - repeat_mask

        def get_packet(bit_index):
            seek = int(offset + math.floor((bit_index / 8.0)))
            start = (bit_index % 8)
            count = int(math.ceil((start + packet_size) / 8.0))
            bits = 0
            for i in range(count):
                assert seek + i <= len(raw)
                bits += struct.unpack("<B", raw[seek+i])[0] << i * 8
            packet = (bits >> start) & packet_mask
            return packet

        def decode_tile(bit_index):
            packet = get_packet(bit_index)
            repeat_mode = packet & repeat_mask
            double_mode = packet & double_mask if repeat_mode else 0
            count = packet & count_mask if repeat_mode else 0

            if repeat_mode:
                first = get_packet(bit_index + packet_size)
                if double_mode:
                    second = get_packet(bit_index + packet_size * 2)
                    return {
                        "next" : bit_index + packet_size * 3,
                        "mode" : "double-repeat",
                        "data" : (first & tile_mask, second & tile_mask),
                        "count" : count,
                    }
                else:
                    return {
                        "next" : bit_index + packet_size * 2,
                        "mode" : "single-repeat",
                        "data" : first & tile_mask,
                        "count" : count,
                    }
            else:
                return {
                    "next" : bit_index + packet_size,
                    "mode" : "single",
                    "data" : packet & tile_mask,
                }

        # now we loop until the tiles array is full
        tiles = []
        stop_at = 64**2
        bit_index = 0
        while len(tiles) < stop_at:
            tile = decode_tile(bit_index)
            bit_index = tile["next"]
            
            if tile["mode"] == "single":
                # draw a singular tile
                tiles.append(tile["data"])

            elif tile["mode"] == "single-repeat":
                # draw a single tile N times
                for i in range(tile["count"]):
                    tiles.append(tile["data"])

            elif tile["mode"] == "double-repeat":
                # draw a pair of tiles N times
                for i in range(tile["count"]):
                    tiles.append(tile["data"][0])
                    tiles.append(tile["data"][1])
            else:
                raise NotImplementedError(
                    "Unknown tile mode: " + tile["mode"])
                    
        assert len(tiles) == stop_at
        for i in range(len(tiles)):
            y = int(math.floor(i/64.0))
            x = i%64
            tile = tiles[i]
            tx = tile % 16
            ty = tile / 16
            bx = ty / 32 * 16 + tx
            by = ty % 32 
            self.board[x][y] = (bx, by)

        if self.version <= Z3_2:
            # Return early for the first two revisions, since we don't
            # what features they support.
            #return
            pass

        after_tiles = int(offset + math.ceil((bit_index / 8.0)))
        remainder = raw[after_tiles:]

        def cut(pattern, data):
            matcher = re.match(pattern, data, re.DOTALL | re.MULTILINE)
            found = matcher.group()
            return found, data[len(found):]

        links, remainder = cut(r'^[^#]*?#\n', remainder)
        self.parse_links(links)

        baddies, remainder = cut(r'^(...[^\n\\]*?\\[^\n\\]*?\\[^\n\\]*?\n)*?\xff\xff\xff\n', remainder)
        self.parse_baddies(baddies)

        if self.version >= GR_1:
            npcs, remainder = cut(r'^(..[^#]*?#[^\n]*?\n)*?#\n', remainder)
            self.parse_npcs(npcs)

            treasure, remainder = cut(r'^(....\n)*?#\n', remainder)
            self.parse_treasure(treasure)

        if self.version == GR_0:
            mystery, remainder = cut(r'^([^#])*#\n', remainder)
            assert(mystery == "#\n")

        self.parse_signs(remainder)

        
    def parse_links(self, blob):
        pattern = r'^(.+) (\d+) (\d+) (\d+) (\d+) ([^\s]+) ([^\s]+)$'
        flags = re.MULTILINE
        links = re.findall(pattern, blob, flags)
        for link_params in links:
            self.add_link(*link_params)


    def parse_baddies(self, blob):
        pattern = r'^(.)(.)(.)([^\n\\]*?)\\([^\n\\]*?)\\([^\n\\]*?)$'
        flags = re.DOTALL | re.MULTILINE
        baddies = re.findall(pattern, blob, flags)
        for baddy in baddies:
            # is guess
            x, y, kind = map(ord, baddy[:3])
            assert(kind <= 9)
            strings = baddy[3:]
            self.add_baddy(x, y, kind, strings)


    def parse_npcs(self, blob):
        pattern = r'^(.)(.)([^#]*)#([^\n]*?)$'
        flags = re.DOTALL | re.MULTILINE
        npcs = re.findall(pattern, blob, flags)
        for params in npcs:
            npc_x = ord(params[0]) - 32
            npc_y = ord(params[1]) - 32
            npc_img = params[2]
            npc_src = params[3].replace("\xa7", "\n")
            if self.version == GR_1 and not npc_img:
                garbage = r'^(\xff|.*?\\.*?\\.*?)$'
                if (re.match(garbage, npc_src) or not npc_src):
                    continue
            self.add_actor(npc_x, npc_y, npc_img, npc_src)


    def parse_treasure(self, blob):
        pattern = r'^(.)(.)(.)(.)$'
        flags = re.DOTALL | re.MULTILINE
        treasures = re.findall(pattern, blob, flags)
        for treasure in treasures:
            x, y, kind, sign = map(lambda x: ord(x)-32, treasure)
            if x >= -1 and x <= 63 and \
               y >= -1 and y <= 63 and \
               kind >= 0 and \
               sign >= -1:
                self.add_treasure(x, y, kind, sign)
            else:
                # garbage data >_<
                break


    def parse_signs(self, blob):
        pattern = r'^(.)(.)([^\n]*)$'
        flags = re.DOTALL | re.MULTILINE
        signs = re.findall(pattern, blob, flags)

        for sign in signs:
            params = sign
            x = ord(params[0]) - 32
            y = ord(params[1]) - 32
            data = re.findall(r'(v\*e[^f]*f|.)', params[2])
            text = u''
            for char in data:
                if len(char) > 1:
                    # The escape sequence for arbitrary character
                    # codes is a control code, followed by what
                    # decodes to "K(number)".  The integer parsed from
                    # the embeded numeric string is then the character
                    # code for the symbol.
                    values = map(lambda x: GLYPHS[ord(x)-32], char[3:-1])
                    text += chr(int(''.join(values)))
                else:
                    # Char value is a sprite.
                    text += GLYPHS[ord(char)-32]

            self.add_sign(x, y, text)
