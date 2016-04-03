
import os
import sys
from PIL import Image
from nw_parser import parse_tile, parse_npcs


TILE_SIZE = 16


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
            tile_x, tile_y = board[x][y]["board"]
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
            value = sum(old[:3])/3.0 * old[3]
            alpha = value * effect[3]
            # red = old[0] * effect[0]
            # grn = old[1] * effect[1]
            # blu = old[2] * effect[2]
            new = map(lambda x: int(x*255), effect[:3]+[alpha])
            px[x,y] = tuple(new)
            

def add_actors(out_img, actors):
    for npc in actors:
        if npc["img"]:
            img_path = npc["img"]            
            img = Image.open(img_path).convert("RGBA")
                                
            shape = npc["area"]
            sprite = img.crop(make_box(*shape))

            if npc["effect"]:
                apply_effect(sprite, npc["effect"])

            x = npc["x"] * TILE_SIZE
            y = npc["y"] * TILE_SIZE
            paste_shape = [x, y] + list(sprite.size)

            if npc["zoom"]:
                new_x, new_y, new_w, new_h, scale = npc["zoom"]
                sprite = sprite.resize([new_w, new_h])
                x = new_x * TILE_SIZE
                y = new_y * TILE_SIZE
                paste_shape = [x, y] + list(sprite.size)
            
            paste_box = make_box(*paste_shape)
            bg = out_img.crop(paste_box)
            mixed = Image.alpha_composite(bg, sprite)
            out_img.paste(mixed, paste_box)

            
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
    
    board = parse_tile(level_path)
    tiles = tile_segments(tiles_path)
    out_img = generate_map(board, tiles)
    add_actors(out_img, parse_npcs(level_path))
    out_img.convert("RGB").save(out_path)
