# Fictional demo samples

Everything here is **fictional**. No names, businesses or amounts belong to real people.

| File | What it shows |
|---|---|
| `notebooks/notebook_a_page2.png` | Notebook A: sales, a debt with a smudged quantity (Musa, 61%), expense, restock, and a written total |
| `notebooks/notebook_b_page3.png` | Notebook B: messy mixed Hausa/English, an OCR-confusable amount (`8,5OO`), an illegible amount (`?,000`), and a written total that disagrees |
| `notebooks/notebook_c_page4.png`, `notebook_c_page5.png` | Notebook C: several customers on credit, then repayments by the same customers. These are loaded as the demo account's history. |
| `voice/voice_note_1.wav` | Synthetic English voice note (Windows TTS) with three transactions |

Each `*.ocr.json` / `*.transcript.json` file is the **pre-recorded reading** returned by
the offline demo providers for that exact file, matched by SHA-256. They let the demo
run without internet. The UI labels these results *Demo reading (offline)*. Any other
file goes to the configured real provider, such as Huawei OCR.

`manifest.json` lists the samples offered on the Capture screen in demo mode.

To regenerate the samples after editing `generate_samples.py`:

```bash
powershell -File samples/voice/make_voice.ps1              # Windows only: synthesise the voice note
backend/.venv/Scripts/python samples/generate_samples.py  # renders pages, writes fixtures + manifest
```

Pages are rendered with the Windows *Ink Free* font when it is available, with a
fallback otherwise. Regenerating changes the image hashes, and the fixtures are
rewritten to match.
