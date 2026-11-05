#!/usr/bin/env python3
"""
doodle-poster / compose.py

把一张真实照片做成「白底 + 手写短句 + 黑色涂鸦小人」的海报。
主体抠图用 macOS Vision，版式与涂鸦由本脚本确定性绘制，不依赖任何生图模型。

示例:
  python3 compose.py --image ~/Downloads/a.jpg --figures figs.json --out poster.jpg
  python3 compose.py --image a.heic --text "先来一块" --out p.jpg      # 只出主体+文字
"""

import argparse
import glob
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
BIN = HERE / "bin" / "cutout"
BLACK = (18, 18, 18, 255)

RATIOS = {
    "3:4": (1536, 2048),
    "4:5": (1536, 1920),
    "1:1": (1600, 1600),
    "9:16": (1440, 2560),
    "2:3": (1400, 2100),
}


# ---------------- 字体 ----------------
def resolve_font(explicit=None):
    if explicit:
        return explicit, True
    pats = [
        "/System/Library/AssetsV2/**/LingWaiSC*.otf",
        "/System/Library/AssetsV2/**/*Handwriting*.otf",
        "/System/Library/AssetsV2/**/Hannotate*.ttc",
    ]
    for p in pats:
        hits = sorted(glob.glob(p, recursive=True))
        if hits:
            return hits[0], True
    for p in ["/System/Library/Fonts/Supplemental/Hannotate.ttc",
              "/System/Library/Fonts/Supplemental/HanziPen.ttc",
              "/System/Library/Fonts/STHeiti Light.ttc",
              "/System/Library/Fonts/PingFang.ttc"]:
        if os.path.exists(p):
            return p, False
    return None, False


# ---------------- 抠图 ----------------
def ensure_cutout(image_path):
    if not BIN.exists():
        subprocess.run(["bash", str(HERE / "prepare.sh")], check=True,
                       stdout=subprocess.DEVNULL)
    h = hashlib.md5(f"{image_path}:{os.path.getmtime(image_path)}".encode()).hexdigest()[:12]
    out = Path(tempfile.gettempdir()) / f"doodle_cut_{h}.png"
    if not out.exists():
        subprocess.run([str(BIN), str(image_path), str(out)], check=True,
                       stdout=subprocess.DEVNULL)
    return out


def clean_alpha(img):
    """补掉木板缝、叶片间隙这类被误判成背景的小洞"""
    from PIL import ImageChops  # noqa: F401
    alpha = img.getchannel("A")
    solid = alpha.point(lambda v: 255 if v > 40 else 0)
    probe = solid.copy()
    w, h = probe.size
    for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        try:
            ImageDraw.floodfill(probe, seed, 128)
        except Exception:
            pass
    holes = probe.point(lambda v: 255 if v == 255 else 0)
    fixed = ImageChops.lighter(solid, holes)
    fixed = Image.composite(Image.new("L", img.size, 255), alpha, fixed)
    return fixed.filter(ImageFilter.GaussianBlur(0.8))


def load_subject(image_path):
    p = Path(image_path)
    if p.suffix.lower() in (".heic", ".heif"):
        jpg = Path(tempfile.gettempdir()) / (p.stem + "_conv.jpg")
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "95",
                        str(p), "--out", str(jpg)], check=True, stdout=subprocess.DEVNULL)
        p = jpg
    cut = Image.open(ensure_cutout(p)).convert("RGBA")
    cut.putalpha(clean_alpha(cut))
    bbox = cut.getbbox()
    if not bbox:
        raise SystemExit("抠图失败：没有识别到主体")
    return cut.crop(bbox)


# ---------------- 画笔 ----------------
class Pen:
    def __init__(self, canvas, seed=7):
        self.c = canvas
        self.d = ImageDraw.Draw(canvas)
        random.seed(seed)

    def stroke(self, pts, width=5, jitter=1.0):
        dense = []
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            n = max(2, int(math.hypot(x2 - x1, y2 - y1) / 3))
            for t in range(n):
                s = t / n
                dense.append((x1 + (x2 - x1) * s + random.uniform(-jitter, jitter),
                              y1 + (y2 - y1) * s + random.uniform(-jitter, jitter)))
        dense.append((pts[-1][0] + random.uniform(-jitter, jitter),
                      pts[-1][1] + random.uniform(-jitter, jitter)))
        self.d.line(dense, fill=BLACK, width=width, joint="curve")
        for p in dense:
            self.d.ellipse([p[0] - width / 2, p[1] - width / 2,
                            p[0] + width / 2, p[1] + width / 2], fill=BLACK)

    def circle(self, cx, cy, r, width=5, jitter=1.1, gap=0.12):
        pts, n, start = [], 26, random.uniform(0, 0.6)
        for i in range(n + 1):
            a = start + 2 * math.pi * (i / n) * (1 - gap)
            rr = r + random.uniform(-jitter, jitter)
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        self.stroke(pts, width=width, jitter=0.6)

    def person(self, hip, s=1.0, lean=0.0, hands=None, feet=None):
        torso, thigh, shin, arm, hr = 26 * s, 21 * s, 19 * s, 19 * s, 13.5 * s
        hx, hy = hip
        neck = (hx + lean * 0.4, hy - torso)
        self.stroke([neck, hip], width=5, jitter=0.8)
        self.circle(neck[0], neck[1] - hr - 4 * s, hr, width=5)
        sh = (neck[0], neck[1] + 4 * s)

        if feet is None:
            feet = [(hx - 11 * s, hy + thigh + shin), (hx + 11 * s, hy + thigh + shin)]
        for (fx, fy), side in zip(feet, (-1, 1)):
            knee = (hx + (fx - hx) * 0.45 + side * 3 * s, hy + thigh)
            self.stroke([(hx, hy), knee, (fx, fy)], width=5, jitter=0.8)

        if hands is None:
            hands = [(sh[0] - 13 * s, sh[1] + arm * 0.9), (sh[0] + 13 * s, sh[1] + arm * 0.9)]
        for (hx2, hy2), side in zip(hands, (-1, 1)):
            elbow = ((sh[0] + hx2) / 2 + side * 5 * s, (sh[1] + hy2) / 2)
            self.stroke([sh, elbow, (hx2, hy2)], width=5, jitter=0.8)

    def rib(self, cx, cy, w, h, rot=-6):
        pts = []
        for dx, dy in [(-.5, -.4), (.32, -.5), (.5, -.1), (.42, .38), (-.35, .5), (-.5, .1)]:
            a = math.radians(rot)
            pts.append((cx + (dx * w) * math.cos(a) - (dy * h) * math.sin(a),
                        cy + (dx * w) * math.sin(a) + (dy * h) * math.cos(a)))
        self.stroke(pts, width=5)
        self.stroke([(cx - w * .22, cy + h * .05), (cx + w * .16, cy - h * .05)], width=4)

    def arrow(self, a, b, curve=0.0, width=5, head=34):
        mx = (a[0] + b[0]) / 2 + curve
        my = (a[1] + b[1]) / 2
        self.stroke([a, (mx, my), b], width=width, jitter=0.8)
        ang = math.atan2(b[1] - my, b[0] - mx)
        for d in (0.45, -0.45):
            self.stroke([b, (b[0] - head * math.cos(ang + d),
                             b[1] - head * math.sin(ang + d))], width=width, jitter=0.5)


# ---------------- 文字 ----------------
def draw_text(canvas, value, cx, cy, size, font_path, handwritten):
    if not font_path:
        print("warning: 没有找到可用字体，已跳过文字；用 --font 指定字体文件", file=sys.stderr)
        return
    try:
        import numpy as np
    except ImportError:
        np = None
        handwritten = True  # 没有 numpy 就不做形变，直接用手写字体原样
    try:
        font = ImageFont.truetype(font_path, size, index=1)
    except Exception:
        font = ImageFont.truetype(font_path, size)

    pad, tiles, adv = 40, [], []
    for ch in value:
        b = font.getbbox(ch)
        tile = Image.new("RGBA", (b[2] - b[0] + pad * 2, b[3] - b[1] + pad * 2), (0, 0, 0, 0))
        ImageDraw.Draw(tile).text((pad - b[0], pad - b[1]), ch, font=font, fill=BLACK)
        if not handwritten:  # 非手写字体做轻微形变，避免印刷感
            arr = np.array(tile).astype(np.float32)
            h, w = arr.shape[:2]
            gy, gx = np.mgrid[0:h, 0:w]
            nz = np.random.rand(4, 4) * 2 - 1
            field = np.array(Image.fromarray(((nz + 1) * 127).astype("uint8"))
                             .resize((w, h), Image.BICUBIC)).astype(np.float32)
            field = (field - 127) / 127 * 3.4
            dx = (gx + field).clip(0, w - 1).astype(int)
            dy = (gy + field * 1.1).clip(0, h - 1).astype(int)
            tile = Image.fromarray(arr[dy, dx].astype("uint8"))
        tiles.append(tile)
        adv.append(b[2] - b[0] + int(size * 0.02))

    x = cx - sum(adv) / 2
    for tile, a in zip(tiles, adv):
        rot = tile.rotate(random.uniform(-3, 3), resample=Image.BICUBIC, expand=False)
        canvas.alpha_composite(rot, (int(x - pad), int(cy + random.uniform(-size * .04, size * .04) - pad)))
        x += a


# ---------------- 主流程 ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--figures", help="JSON 文件；省略则只出主体+文字")
    ap.add_argument("--ratio", default="3:4", choices=list(RATIOS))
    ap.add_argument("--subject-y", type=float, default=0.50, help="主体中心纵向位置 0-1")
    ap.add_argument("--subject-w", type=float, default=None, help="主体宽度占比，默认自动")
    ap.add_argument("--bg", default="#FFFFFF")
    ap.add_argument("--text", default=None)
    ap.add_argument("--text-x", type=float, default=0.30)
    ap.add_argument("--text-y", type=float, default=0.11)
    ap.add_argument("--text-size", type=int, default=None)
    ap.add_argument("--font", default=None)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--erase", action="append", default=[],
                    help="擦掉画面里的杂物：x0,y0,x1,y1（画布归一化），可重复")
    ap.add_argument("--print-bbox", action="store_true")
    args = ap.parse_args()

    random.seed(args.seed)
    W, H = RATIOS[args.ratio]

    cfg = {}
    if args.figures:
        fp = Path(args.figures)
        if fp.exists():
            cfg = json.loads(fp.read_text())
        elif args.figures.strip().startswith("{"):
            cfg = json.loads(args.figures)
        else:
            raise SystemExit(f"找不到 figures 文件：{args.figures}")

    subject = load_subject(args.image)
    sw = args.subject_w
    if sw is None:
        aspect = subject.width / subject.height
        sw = 1.0 if aspect > 1.9 else (0.92 if aspect > 1.2 else 0.78)
    target_w = int(W * sw)
    scale = target_w / subject.width
    photo = subject.resize((target_w, max(1, int(subject.height * scale))), Image.LANCZOS)
    px = (W - target_w) // 2
    py = int(H * args.subject_y) - photo.height // 2

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.paste(photo, (px, py))
    for spec in args.erase:
        spec = spec.strip()
        if " " in spec:  # 多边形：x0,y0 x1,y1 x2,y2 ...
            pts = [tuple(float(v) for v in p.split(",")) for p in spec.split()]
            mask = Image.new("L", (W, H), 0)
            ImageDraw.Draw(mask).polygon([(x * W, y * H) for x, y in pts], fill=255)
            layer.paste((0, 0, 0, 0), (0, 0), mask)
        else:            # 矩形：x0,y0,x1,y1
            x0, y0, x1, y1 = [float(v) for v in spec.split(",")]
            layer.paste((0, 0, 0, 0), (int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))

    canvas = Image.new("RGBA", (W, H), args.bg)
    shadow = Image.new("L", (W, H), 0)
    shadow.paste(layer.getchannel("A"), (0, max(10, int(H * 0.009))))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(16, int(W * 0.017))))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.putalpha(shadow.point(lambda v: int(v * 0.20)))
    canvas = Image.alpha_composite(canvas, sh)
    canvas.alpha_composite(layer, (0, 0))

    bb = layer.getbbox() or (px, py, px + target_w, py + photo.height)
    bbox = (bb[0] / W, bb[1] / H, bb[2] / W, bb[3] / H)
    if args.print_bbox:
        print(json.dumps({"subject_bbox": [round(v, 4) for v in bbox],
                          "canvas": [W, H]}))

    pen = Pen(canvas, seed=args.seed)

    def P(p):
        return (p[0] * W, p[1] * H)

    for f in cfg.get("figures", []):
        hx, hy = f["hip"]
        if not (0 <= hx <= 1 and 0 <= hy <= 1):
            print(f"warning: 小人 hip 超出画布 {f['hip']}，会被裁掉", file=sys.stderr)
        hands = [P(p) for p in f["hands"]] if f.get("hands") else None
        feet = [P(p) for p in f["feet"]] if f.get("feet") else None
        pen.person(P(f["hip"]), f.get("scale", 1.0), f.get("lean", 0.0), hands, feet)
        prop = f.get("prop")
        if prop:
            c = P(prop["at"])
            if prop.get("type") == "rib":
                pen.rib(c[0], c[1], prop.get("w", 0.055) * W, prop.get("h", 0.032) * H,
                        prop.get("rotate", -6))

    text_cfg = cfg.get("text", {})
    text_value = args.text or text_cfg.get("value")
    if text_value:
        size = args.text_size or text_cfg.get("size") or int(H * 0.077)
        font_path, handwritten = resolve_font(args.font or text_cfg.get("font"))
        draw_text(canvas, text_value,
                  (text_cfg.get("x", args.text_x)) * W,
                  (text_cfg.get("y", args.text_y)) * H,
                  size, font_path, handwritten)

    arrow = cfg.get("arrow")
    if arrow and text_value:
        pen.arrow(P(arrow["from"]), P(arrow["to"]), arrow.get("curve", 24))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() in (".jpg", ".jpeg"):
        canvas.convert("RGB").save(out, quality=94)
        canvas.save(out.with_suffix(".png"))
    else:
        canvas.save(out)
        canvas.convert("RGB").save(out.with_suffix(".jpg"), quality=94)
    print(str(out))


if __name__ == "__main__":
    main()
