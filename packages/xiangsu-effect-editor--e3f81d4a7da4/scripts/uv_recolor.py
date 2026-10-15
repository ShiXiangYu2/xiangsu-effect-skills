"""像塑 UV 面部 / 模型贴图 本地调色工具。

为什么需要它：
  像塑的脸部 UV 贴图（eye / blusher / lips 等）无法用 AI 生图对齐，必须按
  饱和度加权旋转色相做「本地调色」。模型贴图（.omtl 绑定的 PNG）同样不能手改
  材质文件，只能改 PNG 后重新 import 刷新。本脚本把三次换壳任务里验证过的调色
  逻辑固化下来，避免每次凭视觉猜阈值。

两种模式：
  sat_rotate  : 全图色相旋转，旋转量随饱和度线性插值
                rot(S=0)=rot_base，rot(S=1)=rot_full；再 sat*=sat_mul，val+=val_add
                适用：伪素颜/妆容变身（整张贴图往一个色调推）
  range_remap : 按原图色相区间分桶重映射
                适用：模型贴图换色（如香蕉黄皮→草莓粉、蒂绿→薄荷绿、保留棕柄）
                - 普通规则 {hmin,hmax,hue,sat_mul,val_add} 命中即重映射
                - keep 规则 {hmin,hmax,keep:true} 命中则「保持原样」（用于保护某些区域）
                区间支持环绕：hmin>hmax 表示跨 0°（如 350~10）

辅助：
  --analyze   : 输出原图色相 6° 步进分布直方图，用于「先跑分布再定阈值」

用法示例：
  python uv_recolor.py --analyze --src eye.png
  python uv_recolor.py --mode sat_rotate --src eye.png --dst eye_peach.png \
        --rot-base 0 --rot-full 35 --sat-mul 0.72 --val-add 0
  python uv_recolor.py --mode range --src 香蕉_1_color.png --dst 香蕉_strawberry.png \
        --spec banana_spec.json
"""
import argparse
import json
from pathlib import Path

from PIL import Image


def in_range(hd, a, b):
    """命中判定，支持跨 0° 环绕（a>b 表示 [a,360)∪[0,b]）。"""
    if a <= b:
        return a <= hd <= b
    return hd >= a or hd <= b


def sat_rotate(img, rot_base, rot_full, sat_mul, val_add):
    hsv = img.convert("HSV")
    px = hsv.load()
    W, H = hsv.size
    for y in range(H):
        for x in range(W):
            h, s, v = px[x, y]
            hd = h * 360.0 / 255.0
            sd = s / 255.0
            nd = (hd + (rot_base + (rot_full - rot_base) * sd)) % 360.0
            nh = int(round(nd * 255 / 360)) % 256
            ns = min(255, max(0, int(round(s * sat_mul))))
            nv = min(255, max(0, int(round(v + val_add * 255))))
            px[x, y] = (nh, ns, nv)
    return hsv.convert("RGB")


def range_remap(img, rules):
    hsv = img.convert("HSV")
    px = hsv.load()
    W, H = hsv.size
    keep_ranges = [(r["hmin"], r["hmax"]) for r in rules if r.get("keep")]
    remap = [r for r in rules if not r.get("keep")]
    for y in range(H):
        for x in range(W):
            h, s, v = px[x, y]
            hd = h * 360.0 / 255.0
            if any(in_range(hd, a, b) for a, b in keep_ranges):
                continue  # 保护区间：保持原样
            for r in remap:
                if in_range(hd, r["hmin"], r["hmax"]):
                    nd = r["hue"] if r.get("hue") is not None else hd
                    ns = min(255, max(0, int(round(s * r.get("sat_mul", 1.0)))))
                    nv = min(255, max(0, int(round(v + r.get("val_add", 0.0) * 255))))
                    px[x, y] = (int(round(nd * 255 / 360)) % 256, ns, nv)
                    break
    return hsv.convert("RGB")


def analyze(img):
    hsv = img.convert("HSV")
    px = hsv.load()
    W, H = hsv.size
    buckets = [0] * 60  # 6° 一档
    for y in range(H):
        for x in range(W):
            h = px[x, y][0]
            if px[x, y][2] < 8:  # 跳过近黑（透明/阴影噪声）
                continue
            buckets[h * 60 // 256] += 1
    total = sum(buckets) or 1
    lines = []
    for i, c in enumerate(buckets):
        lo, hi = i * 6, (i + 1) * 6
        bar = "#" * int(round(c / total * 40))
        lines.append(f"{lo:3d}-{hi:3d}°: {c:8d} {bar}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="像塑 UV/模型贴图本地调色")
    ap.add_argument("--src", required=True, help="源 PNG 路径")
    ap.add_argument("--dst", help="输出 PNG 路径（sat_rotate / range 模式需要）")
    ap.add_argument("--mode", choices=["sat_rotate", "range"], help="调色模式")
    # sat_rotate 参数
    ap.add_argument("--rot-base", type=float, default=0.0, help="S=0 时色相旋转量(°)")
    ap.add_argument("--rot-full", type=float, default=0.0, help="S=1 时色相旋转量(°)")
    ap.add_argument("--sat-mul", type=float, default=1.0, help="饱和度乘子")
    ap.add_argument("--val-add", type=float, default=0.0, help="明度增量(0~1)")
    # range 参数
    ap.add_argument("--spec", help="range 模式规则 JSON 路径")
    ap.add_argument("--analyze", action="store_true", help="仅输出色相分布直方图")
    a = ap.parse_args()

    src = Path(a.src)
    img = Image.open(src).convert("RGB")

    if a.analyze:
        print(analyze(img))
        return

    if not a.mode:
        ap.error("非 --analyze 模式必须指定 --mode")
    if not a.dst:
        ap.error("--mode 需要 --dst")

    if a.mode == "sat_rotate":
        out = sat_rotate(img, a.rot_base, a.rot_full, a.sat_mul, a.val_add)
    else:  # range
        if not a.spec:
            ap.error("range 模式必须指定 --spec")
        rules = json.load(open(a.spec, encoding="utf-8"))
        out = range_remap(img, rules)

    dst = Path(a.dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)
    print(f"OK saved {dst}  ({out.size[0]}x{out.size[1]})")


if __name__ == "__main__":
    main()
