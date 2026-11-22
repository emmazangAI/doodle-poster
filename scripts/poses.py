#!/usr/bin/env python3
"""
doodle-poster / poses.py

场景姿势库：爬梯子、扫地、游泳、盖被睡觉、躺椅晒太阳、举牌、刷漆、扶风扇、推小车、坐边喝饮料，
以及可单独摆放的线稿道具（ZZZ、气泡、水波、风、桶、冰块、云）。

这是唯一的数据源：
  - compose.py 直接 import 本文件渲染（带手绘抖动）
  - 小工具通过 `python3 poses.py --emit-js <path>` 生成 poses.js（Canvas 渲染）

坐标约定（局部单位，scale=1）：原点为姿势锚点（通常是髋点），x 朝前（翻转时取反），y 朝下。
人体比例：头半径 20，躯干 42，腿长约 62，和小工具里的火柴人一致。

图元：
  {"t": "line",   "p": [[x,y],...], "w": 1, "smooth": bool, "close": bool, "fill": bool}
  {"t": "circle", "c": [x,y], "r": r, "w": 1}
  {"t": "arc",    "c": [x,y], "r": r, "a": [deg0, deg1], "w": 1}   # 角度顺时针，0 朝右
  {"t": "dot",    "c": [x,y], "r": r}
附加标记：
  "prop": true  —— 属于道具，可用 no_prop 隐藏（比如画一架更长的独立梯子时）
  "deco": true  —— 牌子上的占位线，写了 label 时自动隐藏
"""

import json
import math
import sys

HEAD_R = 20


# ---------------- 图元工具 ----------------
def L(*pts, w=1.0, smooth=False, close=False, fill=False, **flags):
    d = {"t": "line", "p": [[round(x, 1), round(y, 1)] for x, y in pts], "w": w}
    if smooth:
        d["smooth"] = True
    if close:
        d["close"] = True
    if fill:
        d["fill"] = True
    d.update(flags)
    return d


def C(x, y, r, w=1.0, **flags):
    d = {"t": "circle", "c": [x, y], "r": r, "w": w}
    d.update(flags)
    return d


def A(x, y, r, a0, a1, w=1.0, **flags):
    d = {"t": "arc", "c": [x, y], "r": r, "a": [a0, a1], "w": w}
    d.update(flags)
    return d


def D(x, y, r, **flags):
    d = {"t": "dot", "c": [x, y], "r": r}
    d.update(flags)
    return d


def tag(prims, **flags):
    for p in prims:
        p.update(flags)
    return prims


def _unit(dx, dy):
    n = math.hypot(dx, dy) or 1.0
    return dx / n, dy / n


def grip(hand, elbow, r=7):
    """手腕处的小爪：沿手臂方向张开的半圈弧，让「扶着」变成「抓住」"""
    ang = math.degrees(math.atan2(hand[1] - elbow[1], hand[0] - elbow[0]))
    ux, uy = _unit(hand[0] - elbow[0], hand[1] - elbow[1])
    return A(round(hand[0] + ux * 2, 1), round(hand[1] + uy * 2, 1), r,
             round(ang - 115, 1), round(ang + 115, 1), w=0.8)


def body(hip, neck, hands, feet, elbows=None, knees=None, grips=True, face=False):
    """标准火柴人：中空圆头 + 躯干 + 两臂两腿；face=True 时加两点眼睛和一道笑"""
    out = []
    ux, uy = _unit(neck[0] - hip[0], neck[1] - hip[1])
    head = (neck[0] + ux * (HEAD_R + 6), neck[1] + uy * (HEAD_R + 6))
    out.append(L(hip, neck))
    out.append(C(round(head[0], 1), round(head[1], 1), HEAD_R, head=True))
    if face:
        hx, hy = head
        out += tag([D(round(hx - 7, 1), round(hy - 3, 1), 1.7),
                    D(round(hx + 7, 1), round(hy - 3, 1), 1.7),
                    A(round(hx, 1), round(hy + 3, 1), 5.5, 25, 155, w=0.6)], faceDeco=True)
    sh = (neck[0] - ux * 4, neck[1] - uy * 4)
    for i, hand in enumerate(hands):
        if elbows:
            el = elbows[i]
        else:
            side = -1 if i == 0 else 1
            el = ((sh[0] + hand[0]) / 2 + side * 5, (sh[1] + hand[1]) / 2 + 4)
        out.append(L(sh, el, hand))
        if grips:
            out.append(grip(hand, el))
    for i, foot in enumerate(feet):
        if knees:
            kn = knees[i]
        else:
            side = -1 if i == 0 else 1
            kn = (hip[0] + (foot[0] - hip[0]) * 0.45 + side * 3, hip[1] + (foot[1] - hip[1]) * 0.5)
        out.append(L(hip, kn, foot))
    return out


def ladder(x0, y0, x1, y1, width=26, step=24):
    """竖梯：左栏 (x0,y0)->(x1,y1)，右栏水平平移 width，横档等距"""
    out = [L((x0, y0), (x1, y1), w=1.05), L((x0 + width, y0), (x1 + width, y1), w=1.05)]
    length = math.hypot(x1 - x0, y1 - y0)
    n = max(2, int(length / step))
    for i in range(n):
        t = (i + 0.6) / (n + 0.2)
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        out.append(L((x, y), (x + width, y), w=0.9))
    return out


def bowl(cx, cy, rx=18, ry=5.5, depth=13):
    """饭碗：椭圆碗口 + 宽浅碗身 + 冒尖的饭（别画成桶：要宽、要浅、要有碗口椭圆）"""
    shell = L((cx - rx, cy), (cx - rx + 2, cy + depth * 0.62), (cx, cy + depth),
              (cx + rx - 2, cy + depth * 0.62), (cx + rx, cy), smooth=True, fill=True, w=1.0)
    rim = L((cx - rx, cy), (cx, cy - ry), (cx + rx, cy), (cx, cy + ry), smooth=True, close=True, w=0.85)
    rice = L((cx - rx + 5, cy + 1), (cx - rx * 0.4, cy - ry - 2), (cx + rx * 0.3, cy - ry - 3),
             (cx + rx - 6, cy + 1), smooth=True, w=0.7)
    return [shell, rim, rice]


def bucket(cx, top, w=30, h=26, drips=False):
    out = [L((cx - w / 2, top), (cx + w / 2, top), (cx + w / 2 - 4, top + h), (cx - w / 2 + 4, top + h), close=True),
           A(cx, top, w / 2, 180, 360, w=0.8)]
    if drips:
        out += [D(cx - w / 2 - 10, top + h + 4, 3), D(cx - w / 2 - 20, top + h + 2, 2.4)]
    return out


def Z(x, y, s, w=0.75):
    return L((x, y), (x + s, y), (x, y + s), (x + s, y + s), w=w)


def cube(x, y, s, rot=8):
    a = math.radians(rot)
    pts = []
    for dx, dy in ((0, 0), (s, 0), (s, s), (0, s)):
        pts.append((x + dx * math.cos(a) - dy * math.sin(a), y + dx * math.sin(a) + dy * math.cos(a)))
    return L(*pts, close=True, w=0.85)


# ---------------- 姿势 ----------------
def _climb():
    # 人在梯子左侧、侧身向上爬：头不压梯栏，手扣栏杆，脚踩横档
    prims = tag(ladder(30, 100, 60, -120), prop=True)
    prims += body(hip=(10, 2), neck=(18, -38),
                  hands=[(56, -86), (53, -58)],
                  feet=[(42, 52), (46, 22)],
                  knees=[(30, 28), (36, -4)])
    return {"name": "爬梯", "base": 100, "prims": prims}


def _sweep():
    hx0, hy0, hx1, hy1 = 20, -62, 76, 50
    dx, dy = _unit(hx1 - hx0, hy1 - hy0)
    nx, ny = dy, -dx
    at = lambda t: (hx0 + (hx1 - hx0) * t, hy0 + (hy1 - hy0) * t)
    a, b = (hx1 - nx * 16, hy1 - ny * 16), (hx1 + nx * 16, hy1 + ny * 16)
    prims = body(hip=(0, 0), neck=(6, -40), hands=[at(0.18), at(0.45)],
                 feet=[(-14, 62), (14, 62)], knees=[(-6, 31), (8, 31)])
    prims += tag([L((hx0, hy0), (hx1, hy1)), L(a, b, w=1.1)]
                 + [L((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t),
                      (a[0] + (b[0] - a[0]) * t + dx * 11, a[1] + (b[1] - a[1]) * t + dy * 11), w=0.7)
                    for t in (0.1, 0.37, 0.63, 0.9)]
                 + [L((98, 20), (106, 30), (104, 40), smooth=True, w=0.75),
                    L((110, 12), (120, 26), (117, 40), smooth=True, w=0.75)]
                 + bucket(-60, 36), prop=True)
    return {"name": "扫地", "base": 62, "prims": prims}


def _swim():
    prims = body(hip=(0, 0), neck=(40, -6),
                 hands=[(94, -38), (0, 16)], elbows=[(62, -34), (22, 12)],
                 feet=[(-62, -2), (-58, 18)], knees=[(-30, -6), (-28, 10)], grips=False)
    prims += tag([C(100, -60, 6, w=0.75), C(112, -80, 8, w=0.75), C(100, -98, 4, w=0.7)], prop=True)
    return {"name": "游泳", "base": 30, "prims": prims}


def _sleep():
    prims = [C(-58, 22, 18),
             L((-40, 40), (-38, 14), (-16, 0), (20, -2), (52, 10), (72, 40), smooth=True),
             L((-44, 40), (78, 40)),
             L((8, 6), (14, 22), w=0.7)]
    prims += tag([Z(-50, -10, 8), Z(-36, -26, 10), Z(-20, -46, 13)], prop=True)
    return {"name": "睡觉", "base": 40, "prims": prims}


def _lounge():
    chair = [L((-66, -24), (-38, 24)), L((-38, 24), (38, 18)),
             L((-36, 24), (-46, 52)), L((30, 19), (40, 52)), L((-42, 38), (35, 35), w=0.8)]
    prims = tag(chair, prop=True)
    prims += body(hip=(-26, 14), neck=(-50, -16),
                  hands=[(-58, -48), (-12, 4)], elbows=[(-34, -40), (-30, 0)],
                  feet=[(24, 14), (32, 16)], knees=[(0, -6), (4, 4)], grips=False)
    umb = [L((50, 52), (38, -96)), A(38, -96, 44, 180, 360), L((38, -140), (38, -148))]
    for i in range(3):
        umb.append(A(round(-6 + 88 / 6 * (2 * i + 1), 1), -96, round(88 / 6, 1), 180, 360, w=0.8))
    prims += tag(umb, prop=True)
    return {"name": "躺椅", "base": 52, "prims": prims}


def _post():
    prims = tag([L((-56, -160), (80, -160), (80, -102), (-56, -102), close=True, fill=True)], prop=True)
    prims += tag([L((-34, -138), (58, -138), w=0.8), L((-34, -122), (24, -122), w=0.8)], prop=True, deco=True)
    prims += body(hip=(0, 0), neck=(0, -42), hands=[(-22, -106), (40, -106)],
                  feet=[(-14, 62), (14, 62)], knees=[(-8, 31), (8, 31)])
    return {"name": "举牌", "base": 62, "label_box": [-52, -158, 76, -104], "prims": prims}


def _paint():
    ex, ey = 58, -100
    dx, dy = _unit(ex - 18, ey + 34)
    nx, ny = -dy, dx
    p1, p2 = (ex - nx * 12, ey - ny * 12), (ex + nx * 12, ey + ny * 12)
    p3, p4 = (p2[0] + dx * 16, p2[1] + dy * 16), (p1[0] + dx * 16, p1[1] + dy * 16)
    at = lambda t: (18 + (ex - 18) * t, -34 + (ey + 34) * t)
    prims = body(hip=(0, 0), neck=(6, -40), hands=[at(0.15), at(0.42)],
                 feet=[(-12, 62), (18, 62)], knees=[(-4, 31), (10, 30)])
    prims += tag([L((18, -34), (ex, ey)), L(p1, p2, p3, p4, close=True),
                  L(((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2), ((p3[0] + p4[0]) / 2, (p3[1] + p4[1]) / 2), w=0.6)]
                 + bucket(-58, 36, drips=True), prop=True)
    return {"name": "刷漆", "base": 62, "prims": prims}


def _fan():
    cx, cy = 58, -44
    fan = [C(cx, cy, 30), C(cx, cy, 5, w=0.8), L((cx, cy + 30), (cx, 56)), L((40, 60), (76, 60)),
           L((76, 60), (92, 63), (104, 56), (114, 62), smooth=True, w=0.75)]
    for k in range(3):
        a = math.radians(-90 + k * 120)
        ca, sa = math.cos(a), math.sin(a)
        pts = [(4, -3), (14, -8), (23, -3), (22, 5), (12, 7), (4, 3)]
        fan.append(L(*[(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts], smooth=True, close=True, w=0.8))
    fan += [L((100, -62), (112, -66), (124, -60), smooth=True, w=0.75),
            L((102, -44), (128, -44), w=0.75),
            L((100, -26), (112, -22), (122, -28), smooth=True, w=0.75)]
    prims = tag(fan, prop=True)
    prims += body(hip=(0, 0), neck=(4, -40), hands=[(55, -4), (55, 14)],
                  feet=[(-14, 62), (14, 62)], knees=[(-6, 31), (8, 31)])
    return {"name": "扶风扇", "base": 62, "prims": prims}


def _cart():
    cart = [L((40, 0), (70, 14)), L((64, 6), (124, 0), (112, 30), (76, 32), close=True),
            C(106, 46, 13), L((92, 31), (106, 46), w=0.8), L((78, 32), (74, 58)),
            cube(80, -16, 16, 6), cube(98, -14, 14, -10), cube(-48, 48, 13, 12)]
    prims = body(hip=(0, 0), neck=(14, -36), hands=[(42, 1), (46, 6)],
                 feet=[(-18, 62), (16, 62)], knees=[(-8, 30), (10, 32)])
    prims += tag(cart, prop=True)
    return {"name": "推小车", "base": 62, "prims": prims}


def _sit_drink():
    prims = body(hip=(0, 0), neck=(0, -42), hands=[(20, -28), (30, -24)],
                 feet=[(28, 34), (20, 36)], knees=[(26, 2), (22, 6)], grips=False)
    prims += tag([L((18, -40), (34, -40), (31, -18), (21, -18), close=True, fill=True, w=0.85),
                  L((28, -40), (36, -54), w=0.7),
                  L((16, -104), (19, -94), w=0.7), L((30, -100), (35, -92), w=0.7), L((4, -108), (5, -98), w=0.7)],
                 prop=True)
    return {"name": "坐着喝", "base": 0, "prims": prims}


def _eat():
    # 抱着饭碗扒饭：碗要宽浅（像碗不像桶），另一手举筷子；脸上带表情
    prims = body(hip=(0, 0), neck=(0, -42), hands=[(-1, -26), (33, -40)],
                 feet=[(-16, 62), (16, 62)], grips=False, face=True)
    prims += tag(bowl(-16, -26) + [L((26, -22), (40, -58), w=0.9), L((30, -20), (44, -56), w=0.9)], prop=True)
    return {"name": "干饭", "base": 62, "prims": prims}


def _worker():
    # 牛马打工人：抱着一台笔记本电脑敲字，旁边冒汗
    laptop = [L((-20, -46), (20, -46), (20, -20), (-20, -20), close=True, w=1.0),   # 屏幕
              L((-20, -20), (20, -20), (24, -12), (-24, -12), close=True, w=1.0),   # 键盘前沿
              L((-13, -16), (13, -16), w=0.6)]                                      # 一排按键
    sweat = [L((21, -82), (25, -88), (21, -93), smooth=True, w=0.7)]
    prims = body(hip=(0, 0), neck=(0, -42), hands=[(-21, -21), (21, -21)],
                 elbows=[(-35, -34), (35, -34)],
                 feet=[(-16, 62), (16, 62)], grips=False, face=True)
    prims += tag(laptop + sweat, prop=True)
    return {"name": "牛马打工人", "base": 62, "prims": prims}


POSES = {
    "climb": _climb(), "sweep": _sweep(), "swim": _swim(), "sleep": _sleep(), "lounge": _lounge(),
    "post": _post(), "paint": _paint(), "fan": _fan(), "cart": _cart(), "sit_drink": _sit_drink(),
    "eat": _eat(), "worker": _worker(),
}


# ---------------- 独立道具 ----------------
PROPS = {
    "zzz": {"name": "ZZZ", "prims": [Z(-26, 10, 12), Z(-6, -8, 16), Z(18, -30, 20)]},
    "bubbles": {"name": "气泡", "prims": [C(-10, 24, 8, w=0.8), C(8, 0, 12, w=0.8), C(-4, -28, 6, w=0.8), C(14, -42, 4, w=0.7)]},
    "waves": {"name": "水波", "prims": [
        L((-40, -6), (-26, -14), (-12, -6), (2, -14), (16, -6), (30, -14), (40, -8), smooth=True, w=0.85),
        L((-24, 12), (-10, 4), (4, 12), (18, 4), (28, 10), smooth=True, w=0.85)]},
    "wind": {"name": "风", "prims": [
        L((-40, -20), (-10, -24), (16, -20), (26, -28), (18, -36), (10, -30), smooth=True, w=0.85),
        L((-30, 0), (30, 0), w=0.85),
        L((-40, 20), (0, 22), (22, 30), (16, 40), (6, 34), smooth=True, w=0.85)]},
    "bucket": {"name": "小桶", "prims": bucket(0, -12, w=48, h=40) + [L((-24, -12), (24, -12), w=0.6)]},
    "cubes": {"name": "冰块", "prims": [cube(-34, 0, 26, 8), cube(4, 8, 22, -12), cube(-8, -26, 18, 20)]},
    "cloud": {"name": "云", "prims": [
        A(-42, 4, 18, 90, 260), A(-14, -12, 24, 195, 330), A(22, -10, 22, 222, 355), A(46, 6, 16, 270, 450),
        L((-44, 22), (46, 22))]},
}


def bbox(prims):
    xs, ys = [], []
    for p in prims:
        if p["t"] == "line":
            for x, y in p["p"]:
                xs.append(x)
                ys.append(y)
        else:
            r = p["r"]
            xs += [p["c"][0] - r, p["c"][0] + r]
            ys += [p["c"][1] - r, p["c"][1] + r]
    return [min(xs) - 8, min(ys) - 8, max(xs) + 8, max(ys) + 8]


for _d in list(POSES.values()) + list(PROPS.values()):
    _d["box"] = [round(v, 1) for v in bbox(_d["prims"])]


# ---------------- 曲线采样（与 JS 版保持同一算法） ----------------
def sample(pts, smooth=False, close=False, steps=8):
    if not smooth or len(pts) < 3:
        return list(pts) + ([pts[0]] if close else [])
    P = list(pts)
    n = len(P)
    out = []
    segs = n if close else n - 1
    for i in range(segs):
        p0 = P[(i - 1) % n] if close else P[max(i - 1, 0)]
        p1 = P[i % n]
        p2 = P[(i + 1) % n] if close else P[min(i + 1, n - 1)]
        p3 = P[(i + 2) % n] if close else P[min(i + 2, n - 1)]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3) for k in (0, 1)))
    out.append(tuple(P[0] if close else P[-1]))
    return out


JS_RUNTIME = r"""
  function sample(pts, smooth, close) {
    if (!smooth || pts.length < 3) return close ? pts.concat([pts[0]]) : pts;
    var n = pts.length, out = [], segs = close ? n : n - 1, steps = 8;
    function at(i) { return close ? pts[(i % n + n) % n] : pts[Math.max(0, Math.min(n - 1, i))]; }
    for (var i = 0; i < segs; i++) {
      var p0 = at(i - 1), p1 = at(i), p2 = at(i + 1), p3 = at(i + 2);
      for (var s = 0; s < steps; s++) {
        var t = s / steps, t2 = t * t, t3 = t2 * t, q = [];
        for (var k = 0; k < 2; k++) {
          q.push(0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 +
            (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3));
        }
        out.push(q);
      }
    }
    out.push(close ? pts[0] : pts[n - 1]);
    return out;
  }

  // 在已经 translate/scale 好的 ctx 上画图元。base 为 scale=1 时的线宽，extra 为白描边额外宽度（局部单位）
  function drawPrims(c, prims, base, extra, opt) {
    opt = opt || {};
    var color = c.strokeStyle;
    c.lineCap = 'round';
    c.lineJoin = 'round';
    for (var i = 0; i < prims.length; i++) {
      var p = prims[i];
      if (p.prop && opt.noProp) continue;
      if (p.faceDeco && opt.noFace) continue;
      if (p.deco && opt.hasLabel) continue;
      var lw = base * (p.w || 1) + extra;
      c.beginPath();
      if (p.t === 'line') {
        var pts = sample(p.p, p.smooth, p.close);
        c.moveTo(pts[0][0], pts[0][1]);
        for (var j = 1; j < pts.length; j++) c.lineTo(pts[j][0], pts[j][1]);
        if (p.fill) { c.fillStyle = '#ffffff'; c.fill(); }
      } else if (p.t === 'circle') {
        c.arc(p.c[0], p.c[1], p.r, 0, Math.PI * 2);
      } else if (p.t === 'arc') {
        c.arc(p.c[0], p.c[1], p.r, p.a[0] * Math.PI / 180, p.a[1] * Math.PI / 180);
      } else if (p.t === 'dot') {
        c.arc(p.c[0], p.c[1], p.r + extra / 2, 0, Math.PI * 2);
        c.fillStyle = color;
        c.fill();
        continue;
      }
      c.lineWidth = lw;
      c.strokeStyle = color;
      c.stroke();
    }
  }
"""


def emit_js(path):
    body_js = (
        "// 由 skills/doodle-poster/scripts/poses.py 生成，请勿手改；改姿势请改 poses.py 后重新 --emit-js\n"
        "(function () {\n  'use strict';\n"
        + JS_RUNTIME
        + "\n  window.DOODLE_POSES = " + json.dumps(POSES, ensure_ascii=False, separators=(",", ":")) + ";\n"
        + "  window.DOODLE_PROPS = " + json.dumps(PROPS, ensure_ascii=False, separators=(",", ":")) + ";\n"
        + "  window.drawDoodlePrims = drawPrims;\n})();\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(body_js)
    print(path)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--emit-js":
        emit_js(sys.argv[2])
    elif len(sys.argv) >= 2 and sys.argv[1] == "--list":
        for k, v in POSES.items():
            print(f"pose  {k:10s} {v['name']}  base={v['base']}  box={v['box']}")
        for k, v in PROPS.items():
            print(f"prop  {k:10s} {v['name']}  box={v['box']}")
    else:
        print("用法: poses.py --list | --emit-js <out.js>")
