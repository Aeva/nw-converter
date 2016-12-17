
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

from common import LevelParser


class DotGraalParser(LevelParser):
    """
    This class takes a path to a .graal encoded file, decodes it, and
    provides a means of easily accessing the contained data.
    """

    def parse(self):
        raw = open(self._uri, "r").read()
        self.version = raw[:8]
        assert(re.match(r'(GR|Z3)-V1.0[1-4]', self.version))

        # we start at 8 to seek just after the file header
        offset = 8
        bits_read = 0

        # tile data is packed in intervals of 13 bits
        packet_size = 13
        packet_mask = (2**packet_size)-1
        repeat_mask = 2**(packet_size-1)
        double_mask = 0x100
        count_mask = 0xFF
        tile_mask = packet_mask - repeat_mask
        
        def get_packet(bit_index):
            # pick out the two characters that contain the bytes for
            # the packet, and unpack them as an unsigned short
            seek = int(offset + math.floor((bit_index / 8.0)))
            chaff = (bit_index % 8)
            pick = struct.unpack("<H", raw[seek:seek+2])[0]

            # bit shift and mask to get the 13 bits that are the
            # actual packet
            packet = (pick >> chaff) & packet_mask
            #import pdb; pdb.set_trace()
            
            # decode data from the packet
            repeat_mode = packet & repeat_mask
            if repeat_mode:
                count = packet & count_mask
                double_mode = packet & double_mask
                return count, double_mode
            else:
                return None, packet & tile_mask

        # now we loop until the tiles array is full
        tiles = []
        stop_at = 64**2
        bit_index = 0
        while len(tiles) < stop_at:
            count, data = get_packet(bit_index)
            bit_index += packet_size
            
            if count is None:
                # draw a singular tile
                tiles.append(data)

            else:
                # packet describes a run length
                packet = get_packet(bit_index)
                bit_index += packet_size
                assert packet[0] is None
                stamp = [packet[1]]
                
                if data:
                    # double repeat mode
                    packet = get_packet(bit_index)
                    bit_index += packet_size
                    assert packet[0] is None
                    stamp.append(packet[1])

                for i in range(count):
                    tiles += stamp
                    
        after_tiles = int(offset + math.ceil((bit_index / 8.0)))
        test = raw[after_tiles:]
        assert len(tiles) == stop_at

        for di in range(len(tiles)):
            tile = tiles[di]
            y = int(math.floor(di/64.0))
            x = di%64
            # the following is wrong, but sorta works:
            tx = di % 16
            ty = di / 16
            bx = ty / 32 * 16 + tx
            by = ty % 32 
            self.board[x][y] = (bx, by)

        
if __name__ == "__main__":
    path = sys.argv[1]
    print "Debug info for parsing file:", path
    level = DotGraalParser(path)
    print " - file version:", level.version
