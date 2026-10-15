"""像塑换壳验收：把预览截图按区域裁剪放大，便于逐区核对贴纸/妆容/头套。

配合 MCP 的 interact_by_dsl(screenshot) 使用：
  1) 用 set_preview_video 设定预览视频（单人 / 宠物猫 / 双源）
  2) interact_by_dsl(reset_preview → wait → screenshot) 落盘一张全屏截图
  3) 本脚本按 regions 把关注区（眼睛/嘴唇/腮红/头套/吉祥物）裁剪放大，输出瓦片

regions 为 JSON 列表，坐标用 0~1 的比例（不依赖分辨率）：
  [{"name":"eye","x":0.30,"y":0.32,"w":0.18,"h":0.10},
   {"name":"lips","x":0.40,"y":0.62,"w":0.20,"h":0.12}]

用法：
  python crop_regions.py --src shot.png --regions regs.json --outdir ./tiles --scale 3
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser(description="预览截图分区放大裁剪")
    ap.add_argument("--src", required=True, help="截图 PNG 路径")
    ap.add_argument("--regions", required=True, help="区域 JSON 路径")
    ap.add_argument("--outdir", required=True, help="输出目录")
    ap.add_argument("--scale", type=float, default=3.0, help="放大倍数")
    ap.add_argument("--label", action="store_true", help="在瓦片上叠加区域名")
    a = ap.parse_args()

    img = Image.open(a.src).convert("RGB")
    W, H = img.size
    regs = json.load(open(a.regions, encoding="utf-8"))
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for r in regs:
        x = int(r["x"] * W)
        y = int(r["y"] * H)
        w = max(1, int(r["w"] * W))
        h = max(1, int(r["h"] * H))
        crop = img.crop((x, y, x + w, y + h))
        if a.scale and a.scale != 1.0:
            crop = crop.resize((max(1, int(w * a.scale)), max(1, int(h * a.scale))),
                               Image.LANCZOS)
        if a.label:
            d = ImageDraw.Draw(crop)
            d.text((4, 4), r["name"], fill=(255, 0, 0))
        out = outdir / f"{r['name']}.png"
        crop.save(out)
        print(f"saved {out}  (src box {x},{y},{x + w},{y + h})")


if __name__ == "__main__":
    main()
