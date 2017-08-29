
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


from nw_parser import DotNWParser
from graal_parser import DotGraalParser


def find_level_parser(level_path):
    for parser in [DotNWParser, DotGraalParser]:
        try:
            return parser(level_path)
        except AssertionError:
            continue
    raise Exception("Unable to determine level file format: %s" % level_path)

def load_level(level_path):
    level = find_level_parser(level_path)
    level.populate()
    return level


def level_debug_info(level_path):
    level = load_level(level_path)
    level.print_debug_info()
