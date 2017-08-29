
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

from parser_common import LevelParser


REVISIONS = ("Z3-V1.01", # <- untested
             "Z3-V1.02", # <- untested
             "Z3-V1.03",
             "Z3-V1.04",
             "GR-V1.01",
             "GR-V1.02",
             "GR-V1.03")

Z3_1 = 0
Z3_2 = 1
Z3_3 = 2
Z3_4 = 3
GR_1 = 4
GR_2 = 5
GR_3 = 6


class DotGraalParser(LevelParser):
    """
    This class takes a path to a .graal encoded file, decodes it, and
    provides a means of easily accessing the contained data.
    """

    def file_version(self):
        assert(self.header in REVISIONS)
        return REVISIONS.index(self.header)

    
    def parse(self):
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
        if links:
            self.parse_links(links)

        # mystery, remainder = cut("\n\xff\xff\xff\n", remainder)
        # if mystery:
        #     # TODO what is this?
        #     # sign text?  treasure boxes?  baddies?
        #     pass

        # if self.version <= Z3_4:
        #     # TODO returning early for now, but it seems like 0xFFFFFF
        #     # is a meaningful delimiter?  Some Z3-V1.04 files have at
        #     # least two sections after block of level links.

        #     # It seems in later revisons, sign text probably appears
        #     # after NPC scripts, so the bit after 'mystery' is
        #     # probably sign text, and 'mystery' is probably baddies or
        #     # treasure boxes.

        #     # Actually
        #     return

        if self.version >= GR_1:
            # GR-V1.01 seems to be when NPCs were introduced.
            # Observations:
            #
            # - 0xA7 seems to be a command delimiter, instead of
            #   semicolons.
            #
            # - Following a script are two "#\n"
            #
            # - After that is a block is binary encoded, but 0x80
            #   shows up several several times in a way that stands
            #   out.  It might be a delimeter, possibly for sign text,
            #   though it might just be my imagination.

            # - In one example though, 'mystery' and 'remainder' both
            #   appear to contain a mix of ascii encoded characters
            #   that spell out words and non-ascii.  I wonder if this
            #   is baddy text or something?  That example does not
            #   have NPCs, though.

            # - "\n\xff\xff\xff\x00\n#\n"?

            # - semicolons are also present in the npc block, so 0xA7
            #   might actually be for newlines instead?
            #
            # - new line character seems to be the delimiter for
            #   individual npcs
            baddies, remainder = cut(r'^(...[^\n\\]*?\\[^\n\\]*?\\[^\n\\]*?\n)*?\xff\xff\xff\n', remainder)
            self.parse_baddies(baddies)

            npcs, remainder = cut(r'^(..[^#]*?#[^\n]+\n)*?#\n', remainder)
            self.parse_npcs(npcs)

        
    def parse_links(self, blob):
        pattern = r'^(.+) (\d+) (\d+) (\d+) (\d+) ([^\s]+) ([^\s]+)$'
        flags = re.MULTILINE
        links = re.findall(pattern, blob, flags)
        for link_params in links:
            self.add_link(*link_params)


    def parse_baddies(self, blob):
        pattern = r'^(.)(.)(.)([^\n\\]*?)\\([^\n\\]*?)\\([^\n\\]*?)$'
        flags = re.MULTILINE
        baddies = re.findall(pattern, blob, flags)
        for baddy in baddies:
            # is guess
            x, y, kind = map(ord, baddy[:3])
            assert(kind <= 9)
            strings = baddy[3:]
            self.add_baddy(x, y, kind, strings)


    def parse_npcs(self, blob):
        pattern = r'^(.)(.)([^#]*)#(.*)$'
        flags = re.MULTILINE
        npcs = re.findall(pattern, blob, flags)
        for params in npcs:
            npc_x = ord(params[0])
            npc_y = ord(params[1])
            npc_img = params[2]
            npc_src = params[3].replace("\xa7", "\n")
            self.add_actor(npc_x, npc_y, npc_img, npc_src)
