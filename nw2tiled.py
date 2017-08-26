
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
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.etree import ElementTree
from xml.dom import minidom

from PIL import Image

from util import load_level
from parser_common import setup_paths, relative_img_path


def pretty_print(elem):
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def encode_as_csv(level):
    data = []
    for y in range(64):
        for x in range(64):
            tile_x, tile_y = level.board[x][y]
            tiled_index = (tile_x + (128 * tile_y)) + 1
            data.append(str(tiled_index))
        
    return ",".join(data)


def set_attrs(element, attrs={}):
    for key, value in attrs.items():
        element.attrib[key] = str(value)
    return element


def create_tileset(pics1_path):
    pics_img = Image.open(pics1_path)
    
    root = Element('tileset')
    set_attrs(root, {
        "name" : os.path.split(pics1_path)[1],
        "tilewidth" : 16,
        "tileheight" : 16,
        "tilecount" : 4096,
        "columns" : 128,
    })
    
    image = SubElement(root, 'image')
    set_attrs(image, {
        "source" : os.path.split(pics1_path)[1],
        "width" : pics_img.size[0],
        "height" : pics_img.size[1],
    })

    return root


def encode_as_tmx(level, tileset_path):
    root = Element('map')
    set_attrs(root, {
        "version" : "1.0",
        "orientation" : "orthogonal",
        "renderorder" : "right-down",
        "width" : 64,
        "height" : 64,
        "tilewidth" : 16,
        "tileheight" : 16,
        "nextobjectid" : 1
    })

    tileset = SubElement(root, 'tileset')
    set_attrs(tileset, {
        "firstgid" : 1,
        "source" : tileset_path,
    })

    ext_start = 32*128 + 1

    npc_tileset = SubElement(root, 'tileset')
    set_attrs(npc_tileset, {
        "firstgid" : ext_start,
        "name" : "extra images",
    })

    map_layer = SubElement(root, 'layer')
    set_attrs(map_layer, {
        "name" : "map",
        "width" : 64,
        "height" : 64,
    })

    data = SubElement(map_layer, 'data')
    data.attrib['encoding'] = "csv"
    data.text = encode_as_csv(level)

    scope = {
        "images" : {},
        "next_gid" : 0,
        "ext_start" : ext_start,
    }
    def index_for_img(src):
        if not scope['images'].has_key(src):
            scope['images'][src] = scope['ext_start'] + scope['next_gid']
            tile = SubElement(npc_tileset, 'tile')
            tile.attrib['id'] = str(scope['next_gid'])
            scope['next_gid'] += 1
            img = SubElement(tile, 'image')
            img.attrib['source'] = relative_img_path(src)
        return scope['images'][src]

    npc_layer = SubElement(root, 'objectgroup')
    npc_layer.attrib['name'] = "npcs"
    obj_id = 0
    for actor in level.actors:
        if not actor.image:
            continue
        obj_id += 1
        obj = SubElement(npc_layer, 'object')
        set_attrs(obj, {
            "id" : obj_id,
            "gid" : index_for_img(actor.image),
            "name" : actor.image.split("/")[-1],
            "x" : actor.x*16,
            "y" : actor.y*16 + actor.clip[3],
        })

    link_layer = SubElement(root, 'objectgroup')
    link_layer.attrib['name'] = "level links"
    link_layer.attrib['color'] = "#ffff00"
    for link in level.links:
        obj_id += 1
        obj = SubElement(link_layer, 'object')
        set_attrs(obj, {
            "id" : obj_id,
            "name" : link.target,
            "type" : "link",
            "x" : link.area[0] * 16,
            "y" : link.area[1] * 16,
            "width" : link.area[2] * 16,
            "height" : link.area[3] * 16,
        })

        props = SubElement(obj, 'properties')
        target = SubElement(props, 'property')
        set_attrs(target, {
            "name" : "warp target",
            "type" : "string",
            "value" : link.target,
        })
        dest_x = SubElement(props, 'property')
        set_attrs(dest_x, {
            "name" : "destination x",
            "type" : "string",
            "value" : link.dest[0],
        })
        dest_y = SubElement(props, 'property')
        set_attrs(dest_y, {
            "name" : "destination y",
            "type" : "string",
            "value" : link.dest[1],
        })

    sign_layer = SubElement(root, 'objectgroup')
    sign_layer.attrib['name'] = "signs"
    sign_layer.attrib['color'] = "#ff0000"
    for sign in level.signs:
        obj_id += 1
        obj = SubElement(sign_layer, 'object')
        set_attrs(obj, {
            "id" : obj_id,
            "name" : "sign",
            "type" : "sign",
            "x" : sign.area[0] * 16,
            "y" : sign.area[1] * 16,
            "width" : sign.area[2] * 16,
            "height" : sign.area[3] * 16,
        })
        props = SubElement(obj, 'properties')
        text = SubElement(props, 'property')
        set_attrs(text, {
            "name" : "sign text",
            "type" : "string",
            "value" : sign.text,
        })
        
    return root


def convert_to_tmx(level_path, tiles_path, sprites_path, out_path):
    setup_paths(sprites_path, out_path)

    tiles_dir = os.path.split(tiles_path)[0]
    tiles_name = os.path.split(tiles_path)[1] + ".tsx"
    output_dir = os.path.split(out_path)[0]
    relative_to_output = os.path.relpath(tiles_dir, output_dir)
    tileset_path = os.path.join(relative_to_output, tiles_name)
    tileset_output_path = os.path.abspath(os.path.join(output_dir, tileset_path))

    if not os.path.isfile(tileset_output_path):
        tileset = create_tileset(tiles_path)
        with open(tileset_output_path, 'w') as output:
            output.write(pretty_print(tileset))

    level = load_level(level_path)
    tmx = encode_as_tmx(level, tileset_path)

    with open(out_path, 'w') as output:
        output.write(pretty_print(tmx))


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
    out_path = os.path.join("out", level_name + ".tmx")

    for path in [level_path, tiles_path]:
        if not os.path.isfile(path):
            print "No such file: " + path
            exit()

    convert_to_tmx(level_path, tiles_path, "sprites", out_path)
