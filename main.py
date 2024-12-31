import sys
import gzip
import xml.etree.ElementTree as ET

def tile_id_to_unicode(tile_id: int) -> str:
    """
    Ranges (standard):
      0..35    : Manzu    (🀇..🀏)  -- 1m..9m
      36..71   : Pinzu    (🀙..🀡)  -- 1p..9p
      72..107  : Souzu    (🀐..🀘)  -- 1s..9s
      108..111 : East     (🀀)
      112..115 : South    (🀁)
      116..119 : West     (🀂)
      120..123 : North    (🀃)
      124..127 : White    (🀆)
      128..131 : Green    (🀅)
      132..135 : Red      (🀄)
    """
    if not (0 <= tile_id <= 135):
        return f"[Invalid tile {tile_id}]"

    # Manzu
    if 0 <= tile_id <= 35:
        rank = tile_id // 4 + 1  # 1..9
        return chr(0x1F007 + (rank - 1))  # 🀇..🀏

    # Pinzu
    elif 36 <= tile_id <= 71:
        rank = (tile_id - 36) // 4 + 1
        return chr(0x1F019 + (rank - 1))  # 🀙..🀡

    # Souzu
    elif 72 <= tile_id <= 107:
        rank = (tile_id - 72) // 4 + 1
        return chr(0x1F010 + (rank - 1))  # 🀐..🀘

    # Honors
    else:
        group = (tile_id - 108) // 4
        honors = ['🀀','🀁','🀂','🀃','🀆','🀅','🀄']
        if 0 <= group < len(honors):
            return honors[group]
        return f"[Invalid honors group {group}]"

def decode_meld(m: int, caller_seat: int):

    offset = m & 0x3
    from_seat = (caller_seat + offset + 1) % 4

    meld_type_val = (m >> 3) & 0x07
    type_map = {
        0: "chi",
        1: "pon",
        2: "nuki",
        3: "ankan",
        4: "kakan",
        5: "minkan",
        6: "unknown",
        7: "unknown",
    }
    meld_type = type_map.get(meld_type_val, "unknown")

    tiles = []

    if meld_type == "chi":
        # bits 10..15 => base (6 bits)
        base = (m >> 10) & 0x3F
        tiles = [base, base+1, base+2]

    elif meld_type == "pon":
        # bits 9..15 => 7 bits
        base = (m >> 9) & 0x7F
        base_tile = base & (~0x3)  # ignore last two bits
        tiles = [base_tile, base_tile, base_tile]

    elif meld_type == "ankan":
        base = (m >> 8) & 0xFF
        base_tile = base & (~0x3)
        tiles = [base_tile, base_tile, base_tile, base_tile]

    elif meld_type == "kakan":
        base = (m >> 8) & 0xFF
        base_tile = base & (~0x3)
        tiles = [base_tile, base_tile, base_tile, base_tile]

    elif meld_type == "minkan":
        base = (m >> 9) & 0x7F
        base_tile = base & (~0x3)
        tiles = [base_tile, base_tile, base_tile, base_tile]

    else:
        pass

    return {
        "type": meld_type,
        "from_seat": from_seat,
        "tiles": tiles
    }

def seat_for_tag(tag: str) -> int:
    draw_map = {'T': 0, 'U': 1, 'V': 2, 'W': 3}
    discard_map = {'D': 0, 'E': 1, 'F': 2, 'G': 3}
    if tag[0] in draw_map:
        return draw_map[tag[0]]
    if tag[0] in discard_map:
        return discard_map[tag[0]]
    return -1

def read_mjlog(filename: str):
    try:
        with gzip.open(filename, "rb") as f:
            xml_data = f.read()
    except OSError:
        with open(filename, "rb") as f:
            xml_data = f.read()

    try:
        root = ET.fromstring(xml_data.decode("utf-8"))
        return root
    except ET.ParseError as e:
        print(f"Error: could not parse XML => {e}")
        return None

def main():

    filename = "./path"
    root = read_mjlog(filename)
    if root is None:
        print("Could not parse .mjlog")
        return

    for elem in root:
        tag = elem.tag
        # Draw/Discard tags: T/U/V/W or D/E/F/G
        seat = seat_for_tag(tag)
        if seat != -1:
            tile_str = tag.lstrip('TUVWDEFG')
            if tile_str.isdigit():
                tile_id = int(tile_str)
                tile_unicode = tile_id_to_unicode(tile_id)
                action = "draws" if tag[0] in "TUVW" else "discards"
                print(f"Seat {seat} {action} {tile_unicode}")
            continue

        # Meld tag: <N who="..." m="...">
        if tag == "N":
            who = int(elem.attrib["who"])
            m_val = int(elem.attrib["m"])
            meld_info = decode_meld(m_val, who)
            meld_type = meld_info["type"]
            from_seat = meld_info["from_seat"]
            tiles_unicode = [tile_id_to_unicode(t) for t in meld_info["tiles"]]
            print(
                f"Seat {who} calls {meld_type.upper()} "
                f"from seat {from_seat}, tiles: {' '.join(tiles_unicode)}"
            )

        # Winning hand: <AGARI ...>
        elif tag == "AGARI":
            who = elem.attrib.get("who", "?")
            fromWho = elem.attrib.get("fromWho", "?")
            hai_str = elem.attrib.get("hai", "")
            tile_ids = [int(x) for x in hai_str.split(",")] if hai_str else []
            tiles_unicode = [tile_id_to_unicode(t) for t in tile_ids]
            print(f"Seat {who} wins from seat {fromWho} with: {' '.join(tiles_unicode)}")

        elif tag == "INIT":
            print("=== New Round (INIT) ===")

if __name__ == "__main__":
    main()
