
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
import sys
import math
import struct

from parser_common import LevelParser


class DotGraalParser(LevelParser):
    """
    This class takes a path to a .graal encoded file, decodes it, and
    provides a means of easily accessing the contained data.
    """

    def file_version(self, reader):
        header = reader.read(8)
        revisions = ("Z3-V1.01", # <- untested
                     "Z3-V1.02", # <- untested
                     "Z3-V1.03",
                     "Z3-V1.04",
                     "GR-V1.01",
                     "GR-V1.02",
                     "GR-V1.03")
        assert(header in revisions)
        return revisions.index(header) + 1

    
    def parse(self):
        raw = open(self._uri, "r").read()

        # we start at 8 to seek just after the file header
        offset = 8
        bits_read = 0

        # tile data is packed in intervals of 12 or 13 bits
        packet_size = 13 if self.version > 5 else 12
        
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
                    
        after_tiles = int(offset + math.ceil((bit_index / 8.0)))
        test = raw[after_tiles:]
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

        
if __name__ == "__main__":
    path = sys.argv[1]
    print "Debug info for parsing file:", path
    level = DotGraalParser(path)
    print " - file version:", level.version
