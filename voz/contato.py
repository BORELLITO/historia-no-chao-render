"""Folha de contato das chapas (miniaturas + id) para QA visual de bordas/recortes. Uso: python voz/contato.py hnc/quarentena saida.jpg"""
import glob, os, sys
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
fs = sorted(glob.glob(sys.argv[1] + "/*.jpg")); W, H, C = 400, 300, 4; rows = (len(fs) + C - 1) // C
sh = Image.new("RGB", (W * C, (H + 18) * rows), (30, 30, 30)); d = ImageDraw.Draw(sh)
for i, f in enumerate(fs):
    im = Image.open(f).convert("RGB"); im.thumbnail((W - 6, H - 6)); x, y = (i % C) * W, (i // C) * (H + 18)
    sh.paste(im, (x + 3, y + 3)); d.text((x + 5, y + H), os.path.basename(f)[:-4] + f" {Image.open(f).size}", fill=(255, 255, 0))
sh.save(sys.argv[2], quality=80)
