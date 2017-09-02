
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
import string
from PIL import Image


TILE_SIZE = 16
SPRITES_PATH = "sprites"
SPRITES_RELATIVE = SPRITES_PATH
OUTPUT_PATH = os.path.abspath('.')


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


def setup_paths(sprites_path, output_path):
    global SPRITES_RELATIVE
    global SPRITES_PATH
    global OUTPUT_PATH
    OUTPUT_PATH = os.path.abspath(output_path) # path to output file
    SPRITES_PATH = os.path.abspath(sprites_path)
    output_dir = os.path.split(OUTPUT_PATH)[0] # directory of output file
    assert os.path.isdir(SPRITES_PATH)
    assert os.path.isdir(output_dir)
    SPRITES_RELATIVE = os.path.relpath(SPRITES_PATH, output_dir)


def relative_img_path(long_path):
    assert os.path.isfile(long_path)
    return os.path.join(
        SPRITES_RELATIVE, os.path.relpath(long_path, SPRITES_PATH))


def img_search(img_name):
    """
    This method recursively searches the "sprites" directory for the
    first image file that matches img_name, and returns its path.

    This is used for looking up the sprite needed to draw NPCs.
    """
    name = ".".join(img_name.split(".")[:-1])
    extensions = ["png", "gif"]
    tree = os.walk(SPRITES_PATH, True, None, True)
    for root, dirnames, filenames in tree:
        for filename in filenames:
            for ext in extensions:
                if filename == name + "." + ext:
                    return os.path.join(root, filename)
    return None


class Actor(object):
    """
    Represents an interactible game object.
    """
    
    def __init__(self, x, y, image, src):
        self.src = src
        self.image = None
        self.x = x
        self.y = y
        self.clip = [0, 0, 0, 0] # [cropx, cropy, width, height]
        self.zoom = None # or, [newx, newy, newwidth, newheight, scale_factor]
        self.effect = None
        self.layer = 0

        if image:
            img_path = img_search(image)
            if img_path:
                try:
                    img = Image.open(img_path)
                    self.image = img_path
                    self.clip = [0, 0, img.size[0], img.size[1]]
                except:
                    print "Cannot find file: %s" % img_path
        self.munge()


    def __move(self, axis, match):
        """
        Move the actor.
        """
        operator, value = match.groups()
        old_value = self.__getattribute__(axis)
        value = float(eval(value.replace(axis, str(old_value))))
        if (operator == "="):
            self.__setattr__(axis, value)
        elif (operator == "+="):
            self.__setattr__(axis, old_value + value)
        elif (operator == "-="):
            self.__setattr__(axis, old_value - value)
        else:
            print "unknown position operator:", operator


    def munge(self):
        """
        Search through the provided script file and attempt to determine
        parameters for rendering this Actor.
        """
        offset_patterns = {}
        offset_patterns['x'] = [
            r'^ *x ?(=) ?((?:x? ?[\d/*+\-. ]+)|(?:[\d/*+\-. ]+ ?x?)) ?;',
            r'^ *x ?(\+=|\-=) ?([\d/*+\-. ]+) ?;',
        ]
        offset_patterns['y'] = [
            regex.replace('x', 'y') for regex in offset_patterns['x']]
        flags = re.DOTALL | re.MULTILINE

        moved = False
        for axis, patterns in offset_patterns.items():
            for refex in patterns:
                found = re.search(regex, self.src, flags)
                if found:
                    self.__move(axis, found)
                moved = True
                break
            
        if self.src.count("setimgpart"):
            pattern = r'setimgpart ([^\s]+?) ?, ?([\d/*+-]+) ??, ?([\d/*+-]+) ??, ?([\d/*+-]+) ??, ?([\d/*+-]+) ?;'
            found = re.findall(pattern, self.src)
            if found:
                self.image = img_search(found[0][0])
                self.clip = map(lambda x: eval(x), found[0][1:])

        if self.src.count("drawaslight;"):
            self.layer = 2

        elif self.src.count("drawunderplayer;"):
            self.layer = -1

        elif self.src.count("drawoverplayer;"):
            self.layer = 1
        
        if self.src.count("setcoloreffect"):
            pattern = r'setcoloreffect ?([\d/*.+-]+) ?, ?([\d/*.+-]+)?, ?([\d/*.+-]+)?, ?([\d/*.+-]+);'
            found = re.findall(pattern, self.src)
            if found:
                try:
                    self.effect = map(lambda x: eval(x) if len(x) > 0 else 0.0, found[0])
                except:
                    print "error parsing:", found[0]
                    self.image = None

        if self.src.count("setzoomeffect"):
            pattern = r'setzoomeffect ?([\d/*.+-]+) ?;'
            found = re.findall(pattern, self.src)
            if found:
                zoom = float(eval(found[0]))
                old_width = self.clip[2]
                new_width = int(old_width * zoom)
                old_height = self.clip[3]
                new_height = int(old_height * zoom)
                new_x = self.x + (((new_width - old_width) / 2.0) * -1) / TILE_SIZE
                new_y = self.y + (((new_height - old_height) / 2.0) * -1) / TILE_SIZE
                self.zoom = [new_x, new_y, new_width, new_height, zoom]

        if self.src.count("join flickerlights;"):
            # 2k1-specific hack.  possibly should just hide images
            # with the word "light" in them if they don't call set
            # effect, but only on levels where at least one npc uses
            # seteffect.
            self.image = None




class Baddy(object):
    def __init__(self, x, y, kind, messages):
        self.x = x
        self.y = y
        self.kind = kind
        assert(len(messages) == 3)
        self.messages = messages




class TreasureBox(object):
    def __init__(self, x, y, kind, sign_index):
        self.x = x
        self.y = y
        self.kind = kind
        self.sign_index = sign_index




class Sign(object):
    def __init__(self, x, y, text):
        self.text = text
        self.area = (x, y, 2, 1) 




class Link(object):
    def __init__(self, target, x, y, w, h, new_x, new_y):
        self.target = target
        self.area = map(int, (x, y, w, h))
        self.dest = (new_x, new_y)




class LevelParser(object):
    """
    Baseclass for level parsers to derrive from.
    """
    
    def __init__(self, path):
        self._uri = path
        with open(self._uri, "r") as reader:
            self.header = reader.read(8)
        self.version = self.file_version()

        self.board = [[None for y in range (64)] for x in range(64)]
        self.links = []
        self.signs = []
        self.actors = []
        self.baddies = []
        self.treasures = []
        self.effects = []

        
    def populate(self):
        self.parse()
        self.actors.sort(self._actor_sort_fn)
        self.find_area_effects()

        
    def file_version(self):
        # Note: This should assert if the file given is not
        # appropriate for the parser.
        raise NotImplementedError("Baseclass method.")

        
    def parse(self):
        raise NotImplementedError("Baseclass method.")

    
    def add_link(self, target, link_x, link_y, width, height, dest_x, dest_y):
        link = Link(target, link_x, link_y, width, height, dest_x, dest_y)
        self.links.append(link)


    def add_baddy(self, x, y, kind, messages):
        self.baddies.append(Baddy(x, y, kind, messages))

        
    def add_actor(self, x, y, image, src):
        self.actors.append(Actor(x, y, image, src))


    def add_treasure(self, x, y, kind, sign):
        self.treasures.append(TreasureBox(x, y, kind, sign))


    def add_sign(self, x, y, text):
        self.signs.append(Sign(x, y, text))


    def print_debug_info(self):
        print "FILE HEADER:"
        print " - %s" % self.header
        print
        print
        print "LEVEL LINKS:"
        for link in self.links:
            print " - {} -> {} {}".format(link.area, link.target, link.dest)
        print
        print
        print "BADDIES:"
        for baddy in self.baddies:
            print " - {} {}".format((baddy.x, baddy.y), baddy.kind)
        print
        print
        print "ACTORS:"
        for actor in self.actors:
            print " - {} {}".format((actor.x, actor.y), actor.image)
            print actor.src
        print
        print
        print "TREASURES:"
        for treasure in self.treasures:
            print " - {} {} {}".format((treasure.x, treasure.y),
                                       treasure.kind, treasure.sign_index)
        print
        print
        print "SIGNS:"
        for sign in self.signs:
            print " - {}".format(sign.area)
            print sign.text
        print
        print

        
    def find_area_effects(self):
        """
        Searches through actor scripts associated with this level, to find
        color filters that might be applied to the level.
        """
        pattern = r'seteffect ?([\d/*.+-]+) ?, ?([\d/*.+-]+)?, ?([\d/*.+-]+)?, ?([\d/*.+-]+);'
        for npc in self.actors:
            found = re.findall(pattern, npc.src)
            if found:
                try:
                    self.effects.append(map(lambda x: float(eval(x)) if len(x) > 0 else 0.0, found[0]))
                except Exception as error:
                    print "error parsing:", found[0]
                    print error

                    
    def _actor_sort_fn(self, lhs, rhs):
        if lhs.layer < rhs.layer:
            return -1
        elif lhs.layer > rhs.layer:
            return 1

        lhs_height = lhs.zoom[3] if lhs.zoom else lhs.clip[3]
        lhs_x = lhs.zoom[0] if lhs.zoom else lhs.x
        lhs_y = lhs.zoom[1] if lhs.zoom else lhs.y

        rhs_height = rhs.zoom[3] if rhs.zoom else rhs.clip[3]
        rhs_x = rhs.zoom[0] if rhs.zoom else rhs.x
        rhs_y = rhs.zoom[1] if rhs.zoom else rhs.y

        a = lhs_y + (lhs_height / TILE_SIZE)
        b = rhs_y + (rhs_height / TILE_SIZE)
            
        if a < b:
            return -1
        elif a > b:
            return 1
        elif lhs_x < rhs_x:
            return -1
        elif lhs_x > rhs_x:
            return 1
        else:
            return 0
