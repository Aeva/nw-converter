
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

import re
import os
import sys
import string
from PIL import Image

from common import LevelParser, Actor, Sign, Link


BASE64 = string.ascii_uppercase + string.ascii_lowercase + string.digits + "+/"



class DotNWParser(LevelParser):
    """
    This class takes a path to a .nw encoded file, decodes it, and
    provides a means of easily accessing the contained data.
    """

    def parse(self):
        with open(self._uri, "r") as reader:
            self.version = reader.read(8)
            reader.seek(0)
            raw_data = reader.read().replace("\r\n", "\n")
            lines = raw_data.split("\n")
        assert self.version == "GLEVNW01"

        pattern = r'BOARD (\d+) (\d+) (\d+) (\d+) ([{0}]+)'.format(BASE64)
        for line in lines:
            match = re.match(pattern, line)
            if match:
                x_start, y_start, run, layer, data = match.groups()
                y = int(y_start)
                for i in range(int(run)*2)[::2]:
                    x = i/2
                    encoded = data[i:i+2]
                    self.board[x][y] = self.decode_tile(encoded)
        self.find_npcs(raw_data)
        self.find_links(raw_data)
        self.find_signs(raw_data)

    
    def decode_tile(self, aa):
        """
        This method is called by parse_tile, and does not need to be
        called directly.  This function takes a pair of characters
        'XX' which represents a number in base64, and determines the
        x,y coordinate encoded in that number.

        The return value is a dictionary that describes the tile.
        """
        lhs = BASE64.index(aa[0])*64
        rhs = BASE64.index(aa[1])
        di = lhs + rhs
        tx = di % 16
        ty = di / 16
        bx = ty / 32 * 16 + tx
        by = ty % 32 
        # tile = {
        #     "code" : aa,
        #     "index" : di,
        #     "__t_xy" : (tx, ty),
        #     "sprite" : (bx, by),
        # }
        return (bx, by)

    
    def find_npcs(self, raw_data):
        pattern = r'^NPC ([^\s]+) (\d+) (\d+)$(.+?)NPCEND$'
        flags = re.DOTALL | re.MULTILINE
        npcs = re.findall(pattern, raw_data, flags)
        for npc in npcs:
            x, y = int(npc[1]), int(npc[2])
            img = npc[0] if npc[0] != '-' else None
            src = npc[3].strip()
            self.actors.append(Actor(img, x, y, src))


    def find_links(self, raw_data):
        pattern = r'^LINK ([^\s]+) (\d+) (\d+) (\d+) (\d+) ([^\s]+) ([^\s]+)$'
        flags = re.DOTALL | re.MULTILINE
        links = re.findall(pattern, raw_data, flags)
        for link in links:
            target = link[0]
            x, y, w, h = map(int, link[1:5])
            dest_x = link[5]
            dest_y = link[6]
            self.links.append(Link(target, x, y, w, h, dest_x, dest_y))


    def find_signs(self, raw_data):
        pattern = r'^SIGN (\d+) (\d+)$(.+?)SIGNEND$'
        flags = re.DOTALL | re.MULTILINE
        signs = re.findall(pattern, raw_data, flags)
        for sign in signs:
            x, y = int(sign[0]), int(sign[1])
            text = sign[2]
            self.signs.append(Sign(x, y, text))




if __name__ == "__main__":
    path = sys.argv[1]
    level = DotNWParser(path)
    for x in range(64):
        row = ""
        for y in range(64):
            tile = level.board[x][y]
            assert tile is not None
            row += tile["code"]
        print row

    for actor in level.actors:
        print "--------------------------------"
        print actor.img
        print actor.src
