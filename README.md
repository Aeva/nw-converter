# Graal Level Converter

This project is a collection of utilities for converting graal
```.nw```, ```.graal```, and ```.zelda``` level files and
corresponding game data into ```.png``` image files or
[Tiled](http://www.mapeditor.org/) ```.tmx``` files.

Users interested in converting their levels into image files will want
to use the ```nw2png.py``` utility.

Users interested in converting their levels into the
[tmx](http://doc.mapeditor.org/en/latest/reference/tmx-map-format/)
map format will want to use the ```nw2tiled.py``` utility instead.

An experimental GTK3 gui is also provided for both use cases.

# Limitations

 - Support for files with the headers ```Z3-V1.01``` or ```Z3-V1.02```
   is speculative, as I don't have any examples to test with.

 - For ```.graal``` and ```.zelda``` files, this project currently can
   only parse tile data.

 - For ```.nw``` files, there is very limited support for NPCs: the
   appearance of NPCs is approximated by pattern matching the NPC's
   gscript.

 - There is currently no support for generating collision data in
   tmx exports.

 - There is no intention to support converting gscript to other
   languages, nor is there any intention to provide a means of
   executing gscript.

## Installation

1. You need
   [python 2.7](https://www.python.org/downloads/release/python-2713/)
   installed on your computer.  Python 3.x is unsupported.  If you are
   using Linux, you probably already have Python 2.7 installed.
2. You need either [Pillow](https://python-pillow.org/) or
   [PIL](http://www.pythonware.com/products/pil/) installed.
3. If you want to use the experimental gui, you will also need
   python-gobject installed, and you will need GTK3.

## Fedora Linux

Fedora Linux users should be able to install all of the dependencies
with this command:

> sudo dnf install python2 python2-pillow python-gobject gtk3

## Windows

Windows users should be warned that while it is technically possible
to run this tool on their system, they will either need some
familiarity with the command line unless using the experimental gui.

Python-gobject is, unfortunately, a significant pain to install on
windows, but the adventurous can try to do so with
[PyGObject for Windows](https://sourceforge.net/projects/pygobjectwin32/files/?source=navbar).

It is planned for the converter gui to eventually be made available as
a stand-alone exe file, but that is not currently an option.

# Usage

Create a directory within this project called sprites and copy your
```pics1.png``` file into that directory, as well as any folders of
images to be used by NPCs.

To convert levels to ```.png``` images, use the ```nw2png.py```
script:

 > python nw2png.py path_to_level.nw [path_to_pics1.png] [output_file.png]

To convert levels to Tiled ```.tmx``` maps, use the ```nw2tiled.py```
script:

 > python nw2tiled.py path_to_level.nw [path_to_pics1.png] [output_file.tmx]

An experimental GTK3 frontend is also available, which supports
conversion to either png or tmx.

 > python converter_gui.py

# Program License

All of the python source files in this repository are released under
the GNU General Public License version 3.

The document ```nw_file_specification.org``` and all example level
files in this repository are released under the Creative Commons
Attribution Share-alike 4.0 license.
