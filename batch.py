
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
import glob

if __name__ == "__main__":
    load_path = sys.argv[1]
    assert os.path.isdir(load_path)
    found = glob.glob(os.path.join(load_path, "*.nw"))
    found += glob.glob(os.path.join(load_path, "*.graal"))
    found += glob.glob(os.path.join(load_path, "*.zelda"))
    found += glob.glob(os.path.join(load_path, "*.editor"))
    picsfile = "sprites/pics1.png"
    if len(sys.argv) > 2:
        picsfile = sys.argv[2]

    cmd = "python nw2png.py {0} {1}"
    for path in found:
        print "\n # # # #  ", os.path.split(path)[-1], "  # # # #"
        os.system(cmd.format(path, picsfile))
    
