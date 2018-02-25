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
    duplicates = {}
    by_hash = {}
    by_path = {}
    for level in sorted(db["levels"], key=sort_fn):
        short_path = os.path.split(level["path"])[-1]
        level_hash = level["level_hash"]
        by_path[short_path] = level

        things = level["signs"] + \
                 level["actors"] + \
                 level["baddies"] + \
                 level["treasures"]
        if things == 0:
            # TODO : Check the pallet hash to see if the level is
            # likely "boring" since it doesn't have anything else in
            # it.  If it is boring, we should still include it in the
            # by_path list, but not in by_hash.
            pass
        
        if by_hash.has_key(level_hash):
            if not duplicates.has_key(level_hash):
                duplicates[level_hash] = []
            duplicates[level_hash].append(level)
        else:
            by_hash[level_hash] = level
        
    return boring, duplicates, by_hash, by_path
    


def generate_setlist(output_path):
    print "Generating level playlist..."

    boring, duplicates, by_hash, by_path = load_corpus()

    visited = []
    paths_written = []
    unprocessed = by_hash.keys()
    queue = []

    quad_count = 0
    pair_count = 0
    ungrouped_count = 0

    def find(key):
        # accepts either the level name or hash
        if key is None:
            return None
        assert(type(key) == str)
        found = None
        if by_path.has_key(key):
            found = by_path[key]
        elif by_hash.has_key(key):
            found = by_hash[key]
        if found and found["level_hash"] not in visited:
            return found
        return None

    def take_level(setlist, level):
        level_hash = level["level_hash"]
        visited.append(level_hash)
        try:
            queue.remove(level_hash)
        except:
            pass
        try:
            unprocessed.remove(level_hash)
        except:
            pass
        assert(level["path"] not in paths_written)
        paths_written.append(level["path"])
        setlist.write(level["path"] + "\n")

    def enqueue(hash_or_path):
        level = find(hash_or_path)
        if level:
            level_hash = level["level_hash"]
            try:
                unprocessed.remove(level_hash)
            except:
                pass
            if level_hash not in queue and level_hash not in visited:
                queue.append(level_hash)
        
    def edge_search(level):
        # this attempts to find near by levels to group together

        if not level["edges"]:
            return None

        left_of = find(level["edges"][1])
        right_of = find(level["edges"][3])

        if not left_of or right_of:
            return None

        east = left_of if left_of else level
        west = level if left_of else right_of
        ne_level, nw_level, se_level, sw_level = None, None, None, None

        if east["edges"][2] and west["edges"][2]:
            ne_level, nw_level = east, west
            se_level = find(east["edges"][2])
            sw_level = find(west["edges"][2])

        elif east["edges"][0] and west["edges"][0]:
            se_level, sw_level = east, west
            ne_level = find(east["edges"][0])
            nw_level = find(west["edges"][0])

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

            level = find(pick)
            assert(level is not None)
            
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
                    take_level(setlist, tile)
                    edges += tile["edges"]
            else:
                ungrouped_count += 1
                edges = level["edges"] or []
                take_level(setlist, level)

            if level["doors"]:
                # add all levels linked by doors into the queue
                for target in level["doors"]:
                    enqueue(target)

            # small chance of adding neighbors into the queue
            for edge_path in set(edges):
                if random.random() <= edge_odds:
                    enqueue(edge_path)

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
