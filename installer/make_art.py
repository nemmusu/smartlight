"""Generate original NSIS welcome/header artwork (Pillow, Windows build host)."""
from __future__ import annotations

from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FONT = Path("C:/Windows/Fonts/segoeui.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")
SCALE = 3


def font(size: int, bold: bool = False):
    path = FONT_BOLD if bold else FONT
    return ImageFont.truetype(str(path), size * SCALE)


def gradient(width: int, height: int) -> Image.Image:
    canvas = Image.new("RGB", (width * SCALE, height * SCALE))
    pixels = canvas.load()
    for y in range(height * SCALE):
        t = y / (height * SCALE)
        for x in range(width * SCALE):
            q = x / (width * SCALE)
            glow = max(0, 1 - math.hypot(q - 0.18, t - 0.52) / 0.88)
            pixels[x, y] = (int(11 + 4 * t + 5 * glow),
                            int(19 + 9 * t + 18 * glow),
                            int(35 + 14 * t + 30 * glow))
    return canvas


def point(x: float, y: float):
    return (round(x * SCALE), round(y * SCALE))


def welcome():
    image = gradient(164, 314)
    draw = ImageDraw.Draw(image)
    # Continuous light path: PC waveform at the bottom, LAN nodes above.
    for i in range(3):
        shift = i * 5
        draw.arc((15 * SCALE, (87 + shift) * SCALE, 149 * SCALE, (221 + shift) * SCALE),
                 215, 512, fill=(24 + i * 6, 135 + i * 13, 202 + i * 9), width=(2 if i == 0 else 1) * SCALE)
    nodes = [(27, 137, 7), (132, 153, 5), (79, 227, 6), (118, 101, 4)]
    for x, y, radius in nodes:
        draw.ellipse((point(x - radius * 1.9, y - radius * 1.9), point(x + radius * 1.9, y + radius * 1.9)),
                     outline=(44, 115, 156), width=SCALE)
        draw.ellipse((point(x - radius, y - radius), point(x + radius, y + radius)), fill=(91, 225, 234))
    draw.line([point(14, 250), point(34, 250), point(42, 239), point(52, 261),
               point(62, 245), point(79, 245), point(92, 254), point(102, 244),
               point(122, 244), point(132, 256), point(150, 256)],
              fill=(82, 227, 228), width=2 * SCALE, joint="curve")
    draw.rounded_rectangle((point(15, 14), point(149, 68)), radius=8 * SCALE,
                           fill=(19, 36, 57), outline=(52, 98, 123), width=SCALE)
    draw.text(point(25, 21), "SMART", font=font(21, True), fill=(240, 249, 255))
    draw.text(point(25, 43), "LIGHT", font=font(18, True), fill=(88, 226, 231))
    draw.text(point(16, 283), "PC  •  TAPO  •  MCP", font=font(8, True), fill=(178, 217, 225))
    draw.line([point(16, 301), point(148, 301)], fill=(47, 82, 106), width=SCALE)
    image.resize((164, 314), Image.Resampling.LANCZOS).save(ROOT / "welcome.bmp")


def header():
    image = gradient(150, 57)
    draw = ImageDraw.Draw(image)
    draw.line([point(12, 29), point(27, 29), point(33, 19), point(43, 39),
               point(50, 26), point(62, 26)], fill=(84, 225, 231), width=3 * SCALE)
    draw.ellipse((point(27, 23), point(32, 28)), fill=(238, 192, 112))
    draw.text(point(69, 12), "SMART", font=font(13, True), fill=(238, 248, 255))
    draw.text(point(69, 29), "LIGHT", font=font(12, True), fill=(88, 226, 231))
    image.resize((150, 57), Image.Resampling.LANCZOS).save(ROOT / "header.bmp")


if __name__ == "__main__":
    welcome()
    header()
    print(ROOT / "welcome.bmp")
    print(ROOT / "header.bmp")
