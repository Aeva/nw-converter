import os
import sys
import glob

if __name__ == "__main__":
    load_path = sys.argv[1]
    assert os.path.isdir(load_path)
    found = glob.glob(os.path.join(load_path, "*.nw"))
    picsfile = "sprites/pics1.png"
    if len(sys.argv) > 2:
        picsfile = sys.argv[2]

    cmd = "python nw2png.py {0} {1}"
    for path in found:
        print "\n # # # #  ", os.path.split(path)[-1], "  # # # #"
        os.system(cmd.format(path, picsfile))
    
