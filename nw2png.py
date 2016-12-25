
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
from PIL import Image
from nw_parser import DotNWParser
from graal_parser import DotGraalParser


TILE_SIZE = 16


def load_level(level_path, sprites_path):
    for parser in [DotNWParser, DotGraalParser]:
        try:
            return parser(level_path, sprites_path)
        except AssertionError:
            continue
    raise Exception("Unable to determine level file format: %s" % level_path)


def make_box(x, y, w=TILE_SIZE, h=TILE_SIZE):
    return map(int, (x, y, x+w, y+h))


def tile_box(x, y):
    return make_box(x * TILE_SIZE, y * TILE_SIZE)


def tile_segments(tiles_path):
    img = Image.open(tiles_path)
    width = img.size[0] / TILE_SIZE
    height = img.size[1] / TILE_SIZE
    tiles = []
    for x in range(width):
        tiles.append([])
        for y in range(height):
            col = tiles[-1]
            box = tile_box(x, y)
            col.append(img.crop(box))
    return tiles


def generate_map(board, tiles):
    img = Image.new('RGBA',(64*16, 64*16))
    for x in range(64):
        for y in range(64):
            tile_x, tile_y = board[x][y]
            try:
                tile = tiles[tile_x][tile_y]
                box = tile_box(x, y)
                img.paste(tile, box)
            except:
                pass
    return img


def apply_effect(img, effect):
    px = img.load()
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            old = map(lambda x: x/255.0, px[x,y])
            new = [int(old[i] * effect[i]*255) for i in range(4)]
            px[x,y] = tuple(new)


def clamp(value, high=1.0, low=0.0):
    return max(min(value, high), low)


def apply_area_effect(img, effect):
    data = img.load()
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            pixel = []
            alpha = clamp(1.0-effect[3])
            for c in range(3):
                darkened = data[x,y][c] * alpha
                tinted = darkened + (effect[c] * 255)
                pixel.append(min(int(tinted), 255))
            data[x,y] = tuple(pixel)
                
            
def add_composite(dest, blit):
    """
    Takes two PIL Image objects of the same size as arguments and adds
    their color channels together, and returns a 3rd image.
    """
    assert dest.size == blit.size
    bg_data = dest.load()
    fg_data = blit.load()
    out = Image.new('RGBA', blit.size)
    out_data = out.load()

    for x in range(blit.size[0]):
        for y in range(blit.size[1]):
            data = []
            alpha = fg_data[x,y][3]/255.0
            for c in range(3):
                lhs = bg_data[x,y][c]
                rhs = int(fg_data[x,y][c] * alpha)
                data.append(min(lhs+rhs, 255))
            data.append(1)
            out_data[x,y] = tuple(data)
    return out


def add_actors(out_img, actors):
    for actor in actors:
        if actor.image:
            img_path = actor.image
            img = Image.open(img_path).convert("RGBA")
                                
            shape = actor.clip
            sprite = img.crop(make_box(*shape))

            if actor.effect:
                apply_effect(sprite, actor.effect)

            x = actor.x * TILE_SIZE
            y = actor.y * TILE_SIZE
            paste_shape = [x, y] + list(sprite.size)

            if actor.zoom:
                new_x, new_y, new_w, new_h, scale = actor.zoom
                sprite = sprite.resize([new_w, new_h])
                x = new_x * TILE_SIZE
                y = new_y * TILE_SIZE
                paste_shape = [x, y] + list(sprite.size)
            
            paste_box = make_box(*paste_shape)
            bg = out_img.crop(paste_box)
            mixed = None
            if actor.effect:
                mixed = add_composite(bg, sprite)
            else:
                mixed = Image.alpha_composite(bg, sprite)
            out_img.paste(mixed, paste_box)


def convert_to_png(level_path, tiles_path, sprites_path, out_path):
    level = load_level(level_path, sprites_path)
    tiles = tile_segments(tiles_path)
    out_img = generate_map(level.board, tiles)
    layers = {
        "normal" : [],
        "light" : [],
    }
    for actor in level.actors:
        if actor.layer < 2:
            layers["normal"].append(actor)
        else:
            layers["light"].append(actor)
    
    add_actors(out_img, layers["normal"])
    if len(level.effects) == 1:
        apply_area_effect(out_img, level.effects[0])
    elif len(level.effects) > 1:
        print "multiple area lighting effects detected"
    
    # TODO apply area lighting here
    add_actors(out_img, layers["light"])
    out_img.convert("RGB").save(out_path)

            
if __name__ == "__main__":
    if len(sys.argv) == 1:
        print "First argument must be a level file."
        exit()

    level_path = sys.argv[1]
    tiles_path = os.path.join("sprites", "pics1.png")
    if len(sys.argv) >= 3:
        tiles_path = sys.argv[2]

    level_name = os.path.split(level_path)[-1]
    if len(sys.argv) >= 4:
        level_name = sys.argv[3]
    out_path = os.path.join("out", level_name + ".png")

    for path in [level_path, tiles_path]:
        if not os.path.isfile(path):
            print "No such file: " + path
            exit()

    convert_to_png(level_path, tiles_path, "sprites", out_path)
