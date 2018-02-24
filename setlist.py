import os
import sys
import time
import random
import cPickle as pickle
from multiprocessing import Pool
from sh import find
from util import load_level
from parser_common import UnknownFileHeader


# Generate a new UUID to invalidate an old level database.
DATABASE_VERSION = "37590c47-f652-4cb8-864e-db18c0e5e5e7"


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
        edges = (north, east, south, west)

    return {
        "level_hash" : level.level_hash(),
        "pallet_hash" : level.pallet_hash(),
        "path" : path,
        "doors" : doors,
        "edges" : edges,
        "signs" : len(level.signs),
        "actors" : len(level.actors),
        "baddies" : len(level.baddies),
        "treasures" : len(level.treasures),
    }


def build_level_database(input_path):
    print "Generating or regenerating level database."
    print "This may take a long time if a lot of files need to be scanned."
    paths = [p.strip() for p in find(input_path)]

    levels = []
    pool = Pool(processes=4)

    ratio = 100.0 / len(paths)
    processed = 0
    last_percent = 0
    for data in pool.imap_unordered(process_level, paths):
        processed += 1
        percent = int(processed * ratio)
        if percent > last_percent:
            last_percent = percent
            print "... {}%".format(percent)
        
        if not data:
            continue
        levels.append(data)

    db = {
        "levels" : levels,
        "version" : DATABASE_VERSION,
    }

    with open("level_db.pickle", "w") as outfile:
        pickle.dump(db, outfile)


def load_level_database():
    db = None
    failed = False
    try:
        with open("level_db.pickle", "r") as infile:
            db = pickle.load(infile)
            if db["version"] != DATABASE_VERSION:
                failed = True
                print "Level database needs to be regenerated!"
    except IOError:
        failed = True
        print "No level database found!"
    if failed:
        print """
Re-run this script with the argument "--scan" followed by a path to
a folder containing all of the levels you wish to scan.
""".strip()
        exit(1)
    return db


def load_corpus():
    db = load_level_database()
    def sort_fn(level):
        return level["level_hash"] + ":" + level["path"]

    boring = []
    duplicates = []
    by_hash = {}
    by_path = {}
    for level in sorted(db["levels"], key=sort_fn):
        short_path = os.path.split(level["path"])[-1]
        level_hash = level["level_hash"]
        if by_hash.has_key(level_hash):
            # we'll use this path as an alias to the other level in
            # case anything links to it
            other = by_hash[level_hash]
            by_path[short_path] = other
            duplicates.append(level)
            continue

        things = level["signs"] + \
                 level["actors"] + \
                 level["baddies"] + \
                 level["treasures"]
        if things == 0:
            # check to see if the pallet is "boring" and possibly skip
            # the level since it doesn't really have anything in it
            pass

        by_hash[level_hash] = level
        by_path[short_path] = level
        
    return boring, duplicates, by_hash, by_path
    


def generate_setlist(output_path):
    print "Generating level playlist..."

    boring, duplicates, by_hash, by_path = load_corpus()

    unprocessed = by_hash.keys()
    queue = []

    quad_count = 0
    pair_count = 0
    ungrouped_count = 0

    def find(key):
        # accepts either level hash or path part
        if by_path.has_key(key):
            key = by_path[key]["level_hash"]
        if by_hash.has_key(key):
            try:
                return unprocessed.index(key), by_hash[key]
            except ValueError:
                pass
        return -1, None

    def edge_search(level):
        # this attempts to find near by levels to group together

        if not level["edges"]:
            return None

        left_of = find(level["edges"][1])[1]
        right_of = find(level["edges"][3])[1]

        if not left_of or right_of:
            return None

        east = left_of if left_of else level
        west = level if left_of else right_of
        ne_level, nw_level, se_level, sw_level = None, None, None, None

        # FIXME if we selecte a duplicate alias in the east/west pair,
        # then the quad will be bogus, because the links will line up
        # wrong.

        if east["edges"][2] and west["edges"][2]:
            ne_level, nw_level = east, west
            se_level = find(east["edges"][2])[1]
            sw_level = find(west["edges"][2])[1]

        elif east["edges"][0] and west["edges"][0]:
            se_level, sw_level = east, west
            ne_level = find(east["edges"][0])[1]
            nw_level = find(west["edges"][0])[1]

        if ne_level and nw_level and se_level and sw_level:
            return (ne_level, nw_level, se_level, sw_level)
        
        else:
            return (east, west)
        

    with open(output_path, "w") as setlist:
        while len(unprocessed) + len(queue) > 0:
            pick = None
            if len(queue):
                pick = queue.pop(0)
            else:
                pick = unprocessed.pop(0)
            level = by_hash[pick]

            edges = []
            edge_odds = 0.30
            adjacent_group = edge_search(level)
            if adjacent_group:
                if len(adjacent_group) == 2:
                    pair_count += 1
                    setlist.write("*** pair ***\n")
                    edge_odds = 0.20
                elif len(adjacent_group) == 4:
                    quad_count += 1
                    setlist.write("*** quad ***\n")
                    edge_odds = 0.10
                for tile in adjacent_group:
                    corrupted = False # HACK
                    if not tile is level:
                        try:
                            index = unprocessed.index(tile["level_hash"])
                            unprocessed.pop(index)
                        except:
                            corrupted = True # HACK 
                    setlist.write(tile["path"] + "\n")
                    edges += tile["edges"]
                if corrupted: # HACK
                    print "(known bug) quad is likely wrong because of duplicate aliasing:"
                    for tile in adjacent_group:
                        print " ***", tile["path"] 
            else:
                ungrouped_count += 1
                edges = level["edges"]
                setlist.write(level["path"] + "\n")

            if level["doors"]:
                # add all levels linked by doors into the queue
                for target in level["doors"]:
                    index, found = find(target)
                    if found:
                        queue.append(unprocessed.pop(index))

            # small chance of adding neighbors into the queue
            if edges:
                for edge_path in edges:
                    if edge_path:
                        edge_index, edge_level = find(edge_path)
                        if edge_level and random.random() < edge_odds:
                            queue.append(unprocessed.pop(edge_index))

    if boring:
        print "Skipped \"boring\" levels:"
        for level in boring:
            print " -", level["path"]
    if duplicates:
        print "Skipped non-unique levels:"
        for level in duplicates:
            print " -", level["path"]

    print "quads found:", quad_count
    print "pairs found:", pair_count
    print "individuals:", ungrouped_count
    print "total tweets:", quad_count + pair_count + ungrouped_count
    print "total levels:", quad_count * 4 + pair_count * 2 + ungrouped_count


if __name__ == "__main__":
    random.seed(12345)
    start = time.time()
    if len(sys.argv) > 1 and sys.argv[1] == "--scan":
        assert(len(sys.argv) == 3)
        build_level_database(sys.argv[2])
    else:
        output_path = sys.argv[1] if len(sys.argv) > 1 else "playlist.txt"
        generate_setlist(output_path)
    elapsed = time.time() - start
    print "Process complete."
    if elapsed > 60:
        print "Elapsed time in minutes:", elapsed / 60.0
    else:
        print "Elapsed time in seconds:", elapsed
