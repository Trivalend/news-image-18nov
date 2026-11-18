#!/usr/bin/env python3
"""News-image-20261118: a newspaper front page summing up 18 November 2026.

Draws a 1024x1024 PNG with a hand-written 5x7 bitmap font and a pure-stdlib
PNG encoder (zlib + struct). No network, no randomness, no time: two runs
write byte-identical output.

Run: mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
Writes $MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png).
"""

import os
import struct
import zlib

W, H = 1024, 1024

# Palette: newspaper, high contrast.
PAPER = (251, 248, 240)
INK = (17, 17, 17)
RED = (185, 28, 28)
DARKRED = (127, 29, 29)
SKY = (220, 235, 245)
SEA = (30, 90, 138)
DEEPSEA = (18, 64, 102)
ORANGE = (245, 158, 11)
YELLOW = (253, 230, 138)
GREY = (100, 116, 128)
DARKGREY = (55, 65, 81)
GREEN = (31, 122, 58)
BLUE = (29, 78, 216)
WHITE = (255, 255, 255)
LIGHTGREY = (229, 231, 235)

# 5x7 bitmap font, written by hand. Each glyph is 7 rows of 5 bits,
# "1" = ink. Only the characters the front page uses.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "11001", "10101", "10011", "10011", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10011", "10101", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00010", "00100", "00100", "00100"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "01100", "01000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
}


# ---------------------------------------------------------------- canvas
buf = bytearray(W * H * 3)


def set_px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i], buf[i + 1], buf[i + 2] = color


def fill_rect(x, y, w, h, color):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            buf[i], buf[i + 1], buf[i + 2] = color


def rect_border(x, y, w, h, color, t=3):
    fill_rect(x, y, w, t, color)
    fill_rect(x, y + h - t, w, t, color)
    fill_rect(x, y, t, h, color)
    fill_rect(x + w - t, y, t, h, color)


def hline(x, y, w, color, t=2):
    fill_rect(x, y, w, t, color)


def vline(x, y, h, color, t=2):
    fill_rect(x, y, t, h, color)


def line(x0, y0, x1, y1, color, t=2):
    # Bresenham, stamping a small square for thickness.
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        fill_rect(x0 - t // 2, y0 - t // 2, t, t, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def disc(cx, cy, r, color):
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            if (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy) <= r * r:
                set_px(xx, yy, color)


def triangle(x1, y1, x2, y2, x3, y3, color):
    # Filled triangle via barycentric test over its bounding box.
    minx = max(0, min(x1, x2, x3))
    maxx = min(W - 1, max(x1, x2, x3))
    miny = max(0, min(y1, y2, y3))
    maxy = min(H - 1, max(y1, y2, y3))
    d = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    if d == 0:
        return
    for yy in range(miny, maxy + 1):
        for xx in range(minx, maxx + 1):
            a = ((y2 - y3) * (xx - x3) + (x3 - x2) * (yy - y3)) / d
            b = ((y3 - y1) * (xx - x3) + (x1 - x3) * (yy - y3)) / d
            c = 1 - a - b
            if a >= 0 and b >= 0 and c >= 0:
                set_px(xx, yy, color)


# ---------------------------------------------------------------- text
def text_width(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(s, x, y, scale, color):
    cx = x
    for ch in s:
        glyph = FONT.get(ch)
        if glyph is None:
            cx += 6 * scale
            continue
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    fill_rect(cx + col * scale, y + row * scale,
                              scale, scale, color)
        cx += 6 * scale


def draw_text_centered(s, cx, y, scale, color):
    draw_text(s, cx - text_width(s, scale) // 2, y, scale, color)


def wrap_text(s, max_width, scale):
    """Word-wrap to lines that fit max_width px. Returns a list of lines."""
    words = s.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_block(lines, x, y, scale, color, line_h):
    for i, ln in enumerate(lines):
        draw_text(ln, x, y + i * line_h, scale, color)
    return y + len(lines) * line_h


# ---------------------------------------------------------------- PNG
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, w, h, pixels):
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    for yy in range(h):
        raw.append(0)  # filter: none
        raw += pixels[yy * w * 3:(yy + 1) * w * 3]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- icons
def draw_lead_scene(x, y, w, h):
    """Gulf scene: sky, fighter jet, explosion, sea, tanker."""
    fill_rect(x, y, w, h, SKY)
    rect_border(x, y, w, h, INK, 3)
    sea_y = y + h - 92
    fill_rect(x, sea_y, w, h - (sea_y - y), SEA)
    # White wave lines on the sea.
    for wy in (sea_y + 18, sea_y + 44, sea_y + 70):
        for wx in range(x + 14, x + w - 14, 46):
            hline(wx, wy, 26, WHITE, 3)
    # Tanker: dark hull, white bridge at the left end, red funnel.
    tx, ty = x + 52, sea_y - 34
    fill_rect(tx, ty, 220, 36, DARKGREY)
    fill_rect(tx + 16, ty - 30, 52, 30, WHITE)
    fill_rect(tx + 34, ty - 52, 16, 22, RED)
    fill_rect(tx, ty + 36, 220, 4, INK)
    # Explosion starburst above the tanker, right of the bridge.
    ex, ey = x + 238, sea_y - 78
    for dx, dy in ((0, -34), (24, -24), (34, 0), (24, 24), (0, 34),
                   (-24, 24), (-34, 0), (-24, -24)):
        triangle(ex, ey, ex + dx, ey + dy, ex + dx // 2 + 8, ey + dy // 2 - 8,
                 ORANGE)
    disc(ex, ey, 26, ORANGE)
    disc(ex, ey, 15, YELLOW)
    # Fighter jet in side profile, diving at the burst: long fuselage,
    # swept main wing below, tail fin above at the rear.
    jx, jy = x + 60, y + 46
    triangle(jx + 116, jy + 26, jx + 8, jy + 18, jx + 8, jy + 36, DARKGREY)
    triangle(jx + 48, jy + 30, jx + 74, jy + 68, jx + 84, jy + 30, DARKGREY)
    triangle(jx + 12, jy + 20, jx + 28, jy - 2, jx + 32, jy + 20, GREY)
    # Missile trail from the jet's nose to the burst.
    line(jx + 116, jy + 26, ex - 22, ey - 18, INK, 3)
    disc(ex - 26, ey - 22, 5, INK)


def draw_bridge(x, y, w, h):
    """Kerch Bridge: two towers, a broken deck, a fallen span in the water."""
    fill_rect(x, y, w, h, SKY)
    rect_border(x, y, w, h, INK, 3)
    sea_y = y + h - 34
    fill_rect(x, sea_y, w, h - (sea_y - y), SEA)
    # Towers.
    fill_rect(x + 22, y + 26, 12, h - 60, DARKGREY)
    fill_rect(x + w - 34, y + 26, 12, h - 60, DARKGREY)
    # Cables from tower tops to the deck.
    line(x + 28, y + 26, x + 58, y + 62, INK, 2)
    line(x + 28, y + 26, x + 84, y + 62, INK, 2)
    line(x + w - 28, y + 26, x + w - 58, y + 62, INK, 2)
    line(x + w - 28, y + 26, x + w - 84, y + 62, INK, 2)
    # Deck in two pieces with a gap in the middle.
    deck_y = y + 62
    fill_rect(x + 6, deck_y, w // 2 - 22, 10, DARKGREY)
    fill_rect(x + w // 2 + 16, deck_y, w // 2 - 22, 10, DARKGREY)
    # Fallen span, tilted, half sunk.
    triangle(x + w // 2 - 14, sea_y - 6, x + w // 2 + 34, sea_y + 12,
             x + w // 2 + 8, sea_y + 26, DARKGREY)
    fill_rect(x + w // 2 - 18, sea_y - 4, 52, 8, DARKGREY)


def draw_flags(x, y, w, h):
    """Three flags on poles: China, Russia, USA."""
    fill_rect(x, y, w, h, PAPER)
    rect_border(x, y, w, h, INK, 3)
    fw, fh = 44, 28
    gap = (w - 3 * fw) // 4
    # China: red field, one yellow star.
    fx = x + gap
    fill_rect(fx, y + 14, fw, fh, RED)
    disc(fx + 12, y + 26, 5, YELLOW)
    vline(fx - 3, y + 8, 44, INK, 3)
    # Russia: white, blue, red horizontal thirds.
    fx = x + 2 * gap + fw
    fill_rect(fx, y + 14, fw, 10, WHITE)
    fill_rect(fx, y + 24, fw, 9, BLUE)
    fill_rect(fx, y + 33, fw, 9, RED)
    vline(fx - 3, y + 8, 44, INK, 3)
    # USA: red and white stripes, blue canton.
    fx = x + 3 * gap + 2 * fw
    for i in range(4):
        fill_rect(fx, y + 14 + i * 7, fw, 4, RED if i % 2 == 0 else WHITE)
    fill_rect(fx, y + 14, fw, 7, RED)
    fill_rect(fx, y + 14, 20, 14, BLUE)
    vline(fx - 3, y + 8, 44, INK, 3)


# ---------------------------------------------------------------- layout
def draw():
    fill_rect(0, 0, W, H, PAPER)
    rect_border(6, 6, W - 12, H - 12, INK, 4)

    # Masthead.
    draw_text_centered("THE WORLD TODAY", W // 2, 26, 8, INK)
    hline(24, 100, W - 48, INK, 4)

    # Date band: the day, named prominently.
    fill_rect(24, 108, W - 48, 50, RED)
    draw_text_centered("WEDNESDAY 18 NOVEMBER 2026", W // 2, 116, 5, WHITE)

    # --- Lead story: US-Iran war in the Gulf.
    draw_text("US-IRAN WAR ESCALATES", 24, 172, 3, RED)
    draw_text("US HITS IRAN", 24, 200, 6, INK)
    draw_text("IRAN HITS BACK", 24, 250, 6, INK)
    lead = ("US JETS HIT AN IRGC MISSILE SITE ON QESHM ISLAND AND "
            "DESTROYED FIVE IRANIAN TANKERS. IRAN HIT BACK WITH DRONES "
            "AT US RADAR SITES IN BAHRAIN AND KUWAIT AND MISSILES AT "
            "A US BASE IN JORDAN.")
    draw_block(wrap_text(lead, 616, 3), 24, 312, 3, INK, 26)
    draw_lead_scene(656, 166, 344, 374)

    hline(24, 548, W - 48, INK, 3)

    # --- Row 2: Kerch Bridge (left) and Shenzhen summit (right).
    draw_text("KERCH BRIDGE HIT", 24, 562, 4, INK)
    kerch = ("UKRAINE STRUCK THE BRIDGE TO CRIMEA FOR A SECOND NIGHT. "
             "PART OF THE ROAD SPAN FELL INTO THE STRAIT.")
    draw_block(wrap_text(kerch, 330, 3), 24, 600, 3, INK, 26)
    draw_bridge(366, 596, 134, 150)

    draw_text("SUMMIT IN SHENZHEN", 524, 562, 4, INK)
    summit = ("XI, PUTIN AND TRUMP MEET ON THURSDAY. THE FIRST "
              "TRILATERAL SUMMIT OF THE THREE LEADERS.")
    draw_block(wrap_text(summit, 330, 3), 524, 600, 3, INK, 26)
    draw_flags(866, 596, 134, 150)

    hline(24, 762, W - 48, INK, 3)

    # --- Row 3: Ebola, Gaza, COP31.
    fill_rect(24, 778, 320, 6, RED)
    draw_text("EBOLA SURGES", 24, 792, 3, INK)
    ebola = "CASES IN DR CONGO TOP 11,000. DEATHS PASS 5,400."
    draw_block(wrap_text(ebola, 320, 3), 24, 826, 3, INK, 26)

    fill_rect(356, 778, 320, 6, BLUE)
    draw_text("GAZA FACES COLD", 356, 792, 3, INK)
    gaza = "UN WARNS OF MORE COLD DEATHS AS WINTER SETS IN. 1.7M DISPLACED."
    draw_block(wrap_text(gaza, 320, 3), 356, 826, 3, INK, 26)

    fill_rect(688, 778, 312, 6, GREEN)
    draw_text("COP31 DECIDES", 688, 792, 3, INK)
    cop = "TALKS IN ANTALYA ENTER THE FINAL PHASE. 144 ITEMS DISPUTED."
    draw_block(wrap_text(cop, 312, 3), 688, 826, 3, INK, 26)

    hline(24, 936, W - 48, INK, 3)

    # --- Bottom strip: the rest of the day.
    briefs = ("ALSO TODAY: KEMEROVO PLANE CRASH KILLS 19 - US MEASLES AT "
              "A 40-YEAR HIGH - 5.3 QUAKE HITS ROMANIA - PELTOLA WINS "
              "ALASKA SENATE - INDIA BEAT PAKISTAN 2-1 FOR 10TH SAFF "
              "TITLE - TRUMP IN MANILA FOR QUAD TALKS")
    draw_block(wrap_text(briefs, W - 48, 2), 24, 950, 2, INK, 18)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    draw()
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, W, H, buf)
    print("wrote %s (%d bytes, %dx%d)" % (path, size, W, H))


if __name__ == "__main__":
    main()
