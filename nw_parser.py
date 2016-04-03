
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

BASE64 = string.ascii_uppercase + string.ascii_lowercase + string.digits + "+/"
TILE_SIZE = 16


def decode_tile(aa):
    lhs = BASE64.index(aa[0])*64
    rhs = BASE64.index(aa[1])
    di = lhs + rhs
    tx = di % 16
    ty = di / 16
    bx = ty / 32 * 16 + tx
    by = ty % 32 
    tile = {
        "code" : aa,
        "index" : di,
        "__t_xy" : (tx, ty),
        "board" : (bx, by),
    }
    return tile


def parse_tile(path):
    lines = open(path, "r").readlines()
    board = [[None for y in range (64)] for x in range(64)]
    pattern = r'BOARD (\d+) (\d+) (\d+) (\d+) ([{0}]+)'.format(BASE64)

    for line in lines:
        match = re.match(pattern, line)
        if match:
            x_start, y_start, run, layer, data = match.groups()
            y = int(y_start)
            for i in range(int(run)*2)[::2]:
                x = i/2
                encoded = data[i:i+2]
                tile = decode_tile(encoded)
                board[x][y] = tile

    #row = data[line][16:].strip()
    return board


def img_search(img_name):
    name = ".".join(img_name.split(".")[:-1])
    extensions = ["png", "gif"]
    tree = os.walk('sprites', True, None, True)
    for root, dirnames, filenames in tree:
        for filename in filenames:
            for ext in extensions:
                if filename == name + "." + ext:
                    return os.path.join(root, filename)
    return None


def parse_npcs(path):
    leveldata = open(path, "r").read().replace('\r\n', '\n')
    pattern = r'^NPC ([^\s]+) (\d+) (\d+)$(.+?)NPCEND$'
    offset_x_patterns = [
        r'^ *x ?(=) ?((?:x? ?[\d/*+\-. ]+)|(?:[\d/*+\-. ]+ ?x?)) ?;',
        r'^ *x ?(\+=|\-=) ?([\d/*+\-. ]+) ?;',
        ]
    offset_y_patterns = []
    for regex in offset_x_patterns:
        offset_y_patterns.append(regex.replace('x', 'y'))
    
    flags = re.DOTALL | re.MULTILINE
    npcs = re.findall(pattern, leveldata, flags)
    structs = []
    for npc in npcs:
        actor = {
            "img" : None,
            "x" : int(npc[1]),
            "y" : int(npc[2]),
            "area" : [0, 0, 0, 0], # cropx cropy width height
            "zoom" : None, # or, newx, newy, newwidth, newheight, scale_factor
            "src" : npc[3].strip() or '',
            "effect" : None,
            "light" : False,
        }

        def do_move(axis, actor, match):
            operator, value = match.groups()
            value = float(eval(value.replace(axis, str(actor[axis]))))
            if (operator == "="):
                actor[axis] = value
            elif (operator == "+="):
                actor[axis] += value
            elif (operator == "-="):
                actor[axis] -= value
            else:
                print "unknown position operator:", operator

        moved = False
        for regex in offset_x_patterns:
            found = re.search(regex, actor["src"], flags)
            if found:
                do_move('x', actor, found)
                moved = True
                break
            
        for regex in offset_y_patterns:
            found = re.search(regex, actor["src"], flags)
            if found:
                do_move('y', actor, found)
                moved = True
                break
        if moved:
            old_xy = "({0}, {1})".format(*npc[1:3])
            new_xy = "({0}, {1})".format(actor['x'], actor['y'])
            print " - moved", npc[0], "from", old_xy, "to", new_xy
            
        img_path = None
        if actor["src"].count("setimgpart"):
            pattern = r'setimgpart ([^\s]+?) ?, ?([\d/*+-]+) ??, ?([\d/*+-]+) ??, ?([\d/*+-]+) ??, ?([\d/*+-]+) ?;'
            found = re.findall(pattern, actor["src"])
            if found:
                img_path = img_search(found[0][0])
                actor["area"] = map(lambda x: eval(x), found[0][1:])
            
        if img_path is None and npc[0] != "-":
            img_path = img_search(npc[0])
            if img_path:
                img = Image.open(img_path)
                actor["area"][2] = img.size[0]
                actor["area"][3] = img.size[1]

        if actor["src"].count("drawaslight;"):
            actor["light"] = True

        if actor["src"].count("setcoloreffect"):
            pattern = r'setcoloreffect ?([\d/*.+-]+) ?, ?([\d/*.+-]+)?, ?([\d/*.+-]+)?, ?([\d/*.+-]+);'
            found = re.findall(pattern, actor["src"])
            if found:
                try:
                    actor["effect"] = map(lambda x: eval(x) if len(x) > 0 else 0.0, found[0])
                except:
                    print "error parsing:", found[0]
                    img_path = None

        if actor["src"].count("setzoomeffect"):
            pattern = r'setzoomeffect ?([\d/*.+-]+) ?;'
            found = re.findall(pattern, actor["src"])
            if found:
                zoom = float(eval(found[0]))
                old_width = actor["area"][2]
                new_width = int(old_width * zoom)
                old_height = actor["area"][3]
                new_height = int(old_height * zoom)
                old_x = actor["x"]
                new_x = old_x + (((new_width - old_width) / 2.0) * -1) / TILE_SIZE
                old_y = actor["y"]
                new_y = old_y + (((new_height - old_height) / 2.0) * -1) / TILE_SIZE
                actor["zoom"] = [new_x, new_y, new_width, new_height, zoom]

        actor["img"] = img_path;
        structs.append(actor)

    def sort_fn(lhs, rhs):
        if not lhs["light"] and rhs["light"]:
            return -1
        elif lhs["light"] and not rhs["light"]:
            return 1

        lhs_height = lhs["zoom"][3] if lhs["zoom"] else lhs["area"][3]
        lhs_x = lhs["zoom"][0] if lhs["zoom"] else lhs["x"]
        lhs_y = lhs["zoom"][1] if lhs["zoom"] else lhs["y"]

        rhs_height = rhs["zoom"][3] if rhs["zoom"] else rhs["area"][3]
        rhs_x = rhs["zoom"][0] if rhs["zoom"] else rhs["x"]
        rhs_y = rhs["zoom"][1] if rhs["zoom"] else rhs["y"]

        a = lhs_y + lhs_height
        b = rhs_y + rhs_height
        if a<b:
            return -1
        elif a>b:
            return 1
        elif lhs_x < rhs_x:
            return -1
        elif lhs_x > rhs_x:
            return 1
        else:
            return 0
            
    structs.sort(sort_fn)
    return structs
    
    
if __name__ == "__main__":
    path = sys.argv[1]
    board = parse_tile(path)
    for x in range(64):
        row = ""
        for y in range(64):
            tile = board[x][y]
            assert tile is not None
            row += tile["code"]
        print row
    npcs = parse_npcs(path)
    for npc in npcs:
        print "--------------------------------"
        print npc["img"]
        print npc["src"]
