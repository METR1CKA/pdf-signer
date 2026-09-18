# CLAUDE.md

Read [AGENTS.md](AGENTS.md) first. It holds the full conventions, the coordinate system, the
sizing rules and the testing approach. This file only adds what is specific to working here
with Claude Code.

## The short version

tkinter GUI plus PyMuPDF (imported as `import pymupdf as fitz`) that stamps a visual signature
image onto a PDF page. It is not a digital signature: no PAdES, no certificates.

- `main.py` — GUI, preview, click handling.
- `signer.py` — geometry and stamping, no UI.
- `requirements.txt` — `pymupdf` only. No PyPDF2, no Pillow.

## Working notes

**Geometry changes belong in `signer.py`.** If a fix involves where the stamp lands, how big
it is, or how it is clamped to the page, it almost certainly goes in `stamp_rect` or
`stamp_signature`, not in the GUI. `main.py` calls `stamp_rect` for the preview overlay too,
so fixing it in one place fixes both the preview and the output.

**Do not rewrite the GUI unless asked.** It works and it has been verified end to end. Prefer
a targeted edit over regenerating `main.py`.

**Never run `python main.py` to check your work.** It blocks on `mainloop()` and will hang the
session. Use `.venv/bin/python -c "import signer, main; print('ok')"` for a smoke check and
call `signer.py` functions directly for anything substantive. See the testing section of
AGENTS.md for the headless GUI approach if you truly need to drive the widgets.

**Verify coordinate changes against a real file.** The Y axis is flipped between the stored
click position and the `fitz.Rect` that gets stamped. Reasoning about it is not enough: stamp
a fixture and read back `page.get_image_info()[0]["bbox"]` to confirm the center matches the
click.

**Leave `.commandcode/` alone**, and do not commit unless you were asked to.
