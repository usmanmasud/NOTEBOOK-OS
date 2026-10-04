"""Generate the fictional demo notebook pages and their demo OCR fixtures.

All names, businesses and amounts are fictional.

Each page is rendered as a handwritten-style PNG on lined paper. Alongside it we
write `<name>.ocr.json`: the reading the offline demo OCR provider returns for that
exact file (matched by SHA-256), including per-line confidence and bounding boxes.
The fixture text deliberately includes realistic OCR imperfections ("2?", "8,5OO")
where the page is smudged, so the review step has something real to correct.

Run from the repo root with the backend virtualenv:
    backend/.venv/Scripts/python samples/generate_samples.py   (Windows)
    backend/.venv/bin/python samples/generate_samples.py       (macOS/Linux)
"""

import hashlib
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).parent
OUT = ROOT / "notebooks"
W, H = 1240, 1600
MARGIN_X, TOP, LINE_GAP = 150, 230, 92

FONT_CANDIDATES = [
    "C:/Windows/Fonts/Inkfree.ttf",
    "C:/Windows/Fonts/segoepr.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
    "/Library/Fonts/Bradley Hand Bold.ttf",
]

# (drawn text, OCR text returned by the fixture, OCR confidence, smudge?)
PAGES = {
    "notebook_a_page2": {
        "title": "Notebook A — page 2 (sales, debt, expense, restock)",
        "page_number": 2,
        "seed": 2,
        "lines": [
            ("1/10/26", "1/10/26", 0.97, False),
            ("Sold 3 bags rice 45,000", "Sold 3 bags rice 45,000", 0.93, False),
            ("Sold 2 tins oil 18,000", "Sold 2 tins oil 18,000", 0.92, False),
            ("Musa shinkafa 2 20k bashi", "Musa shinkafa 2? 20k bashi", 0.61, True),
            ("Kudin mota 2,500", "Kudin mota 2,500", 0.90, False),
            ("Sayo kaya sukari 5 buhu 150k", "Sayo kaya sukari 5 buhu 150k", 0.88, False),
            ("Total sales 63,000", "Total sales 63,000", 0.95, False),
        ],
    },
    "notebook_b_page3": {
        "title": "Notebook B — page 3 (messy, mixed Hausa/English, unclear amounts)",
        "page_number": 3,
        "seed": 3,
        "messy": True,
        "lines": [
            ("Talata 2/10", "Talata 2/10", 0.86, False),
            ("an sayar wake mudu 4  6,400", "an sayar wake mudu 4 6,400", 0.80, False),
            ("Halima taliya kwali 1 bashi 8,500", "Halima taliya kwali 1 bashi 8,5OO", 0.70, False),
            ("kashe kudin wuta 3k", "kashe kudin wuta 3k", 0.84, False),
            ("sayar gishiri 3,000", "sayar gishiri ?,000", 0.55, True),
            ("Jimla 9,400", "Jimla 9,400", 0.82, False),
        ],
    },
    "notebook_c_page4": {
        "title": "Notebook C — page 4 (several customers on credit)",
        "page_number": 4,
        "seed": 4,
        "lines": [
            ("24/9/26", "24/9/26", 0.96, False),
            ("Sold 4 bags rice 60,000", "Sold 4 bags rice 60,000", 0.94, False),
            ("Ibrahim sukari 1 buhu 15k bashi", "Ibrahim sukari 1 buhu 15k bashi", 0.90, False),
            ("Halima mai 1 galan 6k bashi", "Halima mai 1 galan 6k bashi", 0.89, False),
            ("Kudin haya shago 25,000", "Kudin haya shago 25,000", 0.91, False),
            ("Sold 3 bags sugar 54k", "Sold 3 bags sugar 54k", 0.93, False),
        ],
    },
    "notebook_c_page5": {
        "title": "Notebook C — page 5 (repeat customers, repayments)",
        "page_number": 5,
        "seed": 5,
        "lines": [
            ("26/9/26", "26/9/26", 0.96, False),
            ("Ibrahim ya biya 15k", "Ibrahim ya biya 15k", 0.92, False),
            ("Aisha shinkafa 1 buhu 20k bashi", "Aisha shinkafa 1 buhu 20k bashi", 0.90, False),
            ("Halima ta biya 6,000", "Halima ta biya 6,000", 0.91, False),
            ("Sold 2 bags beans 30,000", "Sold 2 bags beans 30,000", 0.93, False),
            ("Sayo kaya shinkafa 10 buhu 140k", "Sayo kaya shinkafa 10 buhu 140k", 0.88, False),
        ],
    },
}


def load_font(size: int) -> ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def paper(rng: random.Random) -> Image.Image:
    img = Image.new("RGB", (W, H), (250, 247, 236))
    d = ImageDraw.Draw(img)
    for y in range(TOP - 40, H - 60, LINE_GAP):
        d.line([(60, y + 58), (W - 60, y + 58)], fill=(178, 205, 230), width=2)
    d.line([(MARGIN_X - 30, 0), (MARGIN_X - 30, H)], fill=(230, 150, 150), width=3)
    # Light paper grain.
    for _ in range(9000):
        x, y = rng.randrange(W), rng.randrange(H)
        shade = rng.randint(225, 245)
        d.point((x, y), fill=(shade, shade - 3, shade - 12))
    return img


def render(name: str, spec: dict) -> dict:
    rng = random.Random(spec["seed"])
    img = paper(rng)
    font = load_font(54 if spec.get("messy") else 50)
    ink = (28, 44, 120)

    d = ImageDraw.Draw(img)
    d.text((W - 190, 90), f"p.{spec['page_number']}", font=load_font(44), fill=ink)
    d.text((MARGIN_X, 95), "Demo Provisions Store (fictional)", font=load_font(34), fill=(90, 90, 90))

    lines_out = []
    for i, (drawn, ocr_text, conf, smudge) in enumerate(spec["lines"]):
        y = TOP + i * LINE_GAP + rng.randint(-6, 6)
        x = MARGIN_X + rng.randint(-8, 14) + (20 if spec.get("messy") and i % 2 else 0)
        layer = Image.new("RGBA", (W, 130), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.text((x, 20), drawn, font=font, fill=ink + (255,))
        angle = rng.uniform(-1.6, 1.6) * (1.8 if spec.get("messy") else 1)
        layer = layer.rotate(angle, resample=Image.BICUBIC, center=(x, 60))
        img.paste(layer, (0, y - 20), layer)

        left, top, right, bottom = ImageDraw.Draw(img).textbbox((x, y), drawn, font=font)
        pad = 10
        bbox = {
            "x": round((left - pad) / W, 4),
            "y": round((top - pad) / H, 4),
            "width": round((right - left + 2 * pad) / W, 4),
            "height": round((bottom - top + 2 * pad) / H, 4),
        }
        if smudge:
            # Ink smudge over part of the line: the reason the OCR is unsure here.
            sx = left + int((right - left) * 0.42)
            blot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            bd = ImageDraw.Draw(blot)
            bd.ellipse([sx - 40, top - 12, sx + 55, bottom + 14], fill=(60, 70, 140, 120))
            blot = blot.filter(ImageFilter.GaussianBlur(9))
            img.paste(blot, (0, 0), blot)
        lines_out.append({"text": ocr_text, "confidence": conf, "bbox": bbox})

    img = img.filter(ImageFilter.GaussianBlur(0.6))
    png = OUT / f"{name}.png"
    img.save(png, optimize=True)
    data = png.read_bytes()
    fixture = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "source_file": png.name,
        "note": "Pre-recorded demo reading of a fictional sample page. Used only by the offline demo OCR provider.",
        "pages": [{"page_number": spec["page_number"], "width": W, "height": H, "lines": lines_out}],
    }
    (OUT / f"{name}.ocr.json").write_text(json.dumps(fixture, indent=2), encoding="utf-8")
    return {"id": name.replace("_", "-"), "type": "PHOTO", "title": spec["title"],
            "file": f"notebooks/{png.name}", "mime_type": "image/png"}


def voice_samples() -> list[dict]:
    """Register voice samples (WAV files are produced by samples/voice/make_voice.ps1)."""
    entries = []
    for transcript_file in sorted((ROOT / "voice").glob("*.transcript.json")):
        data = json.loads(transcript_file.read_text(encoding="utf-8"))
        wav = ROOT / "voice" / data["source_file"]
        if not wav.exists():
            continue
        data["sha256"] = hashlib.sha256(wav.read_bytes()).hexdigest()
        transcript_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        entries.append({"id": wav.stem.replace("_", "-"), "type": "VOICE", "title": data["title"],
                        "file": f"voice/{wav.name}", "mime_type": "audio/wav"})
    return entries


def main() -> None:
    OUT.mkdir(exist_ok=True)
    samples = [render(name, spec) for name, spec in PAGES.items()]
    samples += voice_samples()
    manifest = {
        "note": "All sample data is fictional. Any resemblance to real people or businesses is coincidental.",
        "samples": samples,
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    for s in samples:
        print(f"{s['id']:24} {s['file']}")


if __name__ == "__main__":
    main()
