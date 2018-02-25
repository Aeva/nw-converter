
import re


def parse(path):
    with open(path, 'r') as infile:
        raw = infile.read()

    reg = r'^SPRITE\s+(\d+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+?(\S?.*?)$'
    sprites = {}
    for key, img, x, y, w, h, hint in re.findall(reg, raw, re.MULTILINE):
        sprites[key] = {
            "img" : img,
            "aabb" : tuple(map(int, (x, y, w, h))),
            "hint" : hint.strip()
        }

    reg = '^DEFAULT(\S+)(\s+?.*?)$'
    defaults = {}
    for key, value in re.findall(reg, raw, re.MULTILINE):
        print key, value.strip()

    singledir = re.search(r'^SINGLEDIRECTION\s*?$', raw, re.MULTILINE)
    score = []
    seeking = True
    for line in raw.split("\n"):
        line = line.strip()
        if seeking:
            if line.startswith("ANI"):
                seeking = False
            continue
        if line.startswith("ANIEND"):
            break

        params = line.split(" ")
        if params[0] in ["WAIT", "PLAYSOUND"] or not line:
            continue
        else:
            score.append(line)

    if not singledir:
        old_score = score
        score = []
        for i in range(len(old_score)/4):
            p = i*4
            frame = old_score[p:p+4]
            score.append(frame)

    return sprites, score

    
