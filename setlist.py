import os
import sys
import time
import random
from multiprocessing import Pool
from sh import find
from util import load_level
from parser_common import UnknownFileHeader


def process_level(path):
    if not os.path.isfile(path):
        return None

    try:
        level = load_level(path, fast_mode = True)
    except UnknownFileHeader:
        return None

    edges = None
    doors = []
    north, east, south, west = None, None, None, None
    for link in level.links:
        x, y, w, h = link.area
        if w > 60:
            if y == 0:
                north = link.target
            elif y == 63:
                south = link.target
        elif h > 60:
            if x == 0:
                west = link.target
            elif x == 63:
                east = link.target
        else:
            doors.append(link.target)
    
    if north or east or south or west:
        edges = [north, east, south, west]

    return level.level_hash(), path, edges, doors or None


def cut_path(path, base_path):
    if path.startswith(base_path):
        return path[len(base_path):]
    else:
        return path
    

if __name__ == "__main__":
    start = time.time()
    paths = [p.strip() for p in find(sys.argv[1])]

    levels = {}
    level_edges = {}
    level_doors = {}
    pool = Pool(processes=4)

    for data in pool.imap_unordered(process_level, paths):
        if not data:
            continue
        level_hash, path, edges, doors = data

        if levels.has_key(level_hash):
            continue
        else:
            short_path = cut_path(path, sys.argv[1])
            levels[level_hash] = short_path
            level_edges[short_path] = edges
            level_doors[short_path] = doors

    elapsed = time.time() - start
    print "level analysis elapsed time in minutes:", elapsed / 60.0
    print "generating set list now"

    paths = levels.values()
    queue = []

    random.seed(12345)
    random.shuffle(paths)

    quad_count = 0
    pair_count = 0
    ungrouped_count = 0

    output_path = sys.argv[2] if len(sys.argv) > 2 else "playlist.txt"
    with open(output_path, "w") as setlist:
        while len(paths) + len(queue) > 0:
            pick = None
            if len(queue):
                pick = queue.pop(0)
            else:
                pick = paths.pop(0)

            quad = False
            pair = False

            edges = level_edges[pick]
            doors = level_doors[pick]

            if edges:
                # See if pick is the north west corner of a 2x2 square
                # of likely mapped levels.  We know east and south
                # already, so we just need to confirm that they're
                # available and then determine what the southeast
                # corner is.  Otherwise, just take a horizontal
                # neighbor and don't bother with the quad.

                north, east, south, west = edges
                diagonal = None
                ne_index, sw_index, se_index = None, None, None

                try:
                    ne_index = paths.index(east)
                    sw_index = paths.index(south)
                except:
                    pass

                if ne_index is not None and sw_index is not None:
                    try:
                        east_of_south = level_edges[south][1]
                        south_of_east = level_edges[east][2]
                        if east_of_south == south_of_east:
                            diagonal = east_of_south
                            se_index = paths.index(east_of_south)
                    except:
                        diagonal = None

                if diagonal:
                    paths.pop(ne_index)
                    paths.pop(sw_index)
                    paths.pop(se_index)

                    setlist.write("*** quad ***\n")
                    setlist.write(pick + "\n")
                    setlist.write(east + "\n")
                    setlist.write(south + "\n")
                    setlist.write(diagonal + "\n")

                    quad = True
                    quad_count += 1

                else:
                    # For whatever reason, we couldn't complete a
                    # quad, so try to take a horizontal neighbor
                    # instead.

                    adjacent = None
                    try:
                        adjacent = paths.index(west)
                        pair = (pick, west)
                    except:
                        try:
                            adjacent = paths.index(east)
                            pair = (east, pick)
                        except:
                            pass
                    if pair:
                        pair_count += 1
                        paths.pop(adjacent)
                        setlist.write("*** pair ***\n")
                        setlist.write(pair[0] + "\n")
                        setlist.write(pair[1] + "\n")

            if doors:# and random.random() < 0.75:
                for link in doors:
                    found = None
                    try:
                        found = paths.index(door)
                    except:
                        pass
                    if found:
                        queue.append(paths.pop(found))

            if edges:
                # last, regardless of what happened regarding quads
                # and pairs, have a chance of throwing the remaining
                # edges into the queue:
                for edge in edges:
                    if edge and random.random() < 0.25:
                        found = None
                        try:
                            found = paths.index(edge)
                        except:
                            pass
                        if found:
                            queue.append(paths.pop(found))

            if not quad and not pair:
                ungrouped_count += 1
                setlist.write(pick + "\n")

    print "quads found:", quad_count
    print "pairs found:", pair_count
    print "individuals:", ungrouped_count
    print "total tweets:", quad_count + pair_count + ungrouped_count
    print "total levels:", quad_count * 4 + pair_count * 2 + ungrouped_count
    print "done!"
