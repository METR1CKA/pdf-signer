# AGENTS.md

Instructions for coding agents working in this repository.

## What this project is

A desktop app that stamps a **visual signature** onto a PDF page. The user picks a document,
picks a signature image or PDF, clicks on the page preview, and saves a signed copy.

This is **not a digital signature**. No PAdES, no certificates, no cryptography, no identity
or integrity guarantees. It draws an image onto a page. Do not add code or documentation that
implies otherwise.

## Stack and layout

- Python 3.10+, tkinter from the standard library, PyMuPDF for all PDF work.
- `main.py` — the tkinter GUI: file pickers, page navigation, preview canvas, click handling,
  and orchestration. No PDF geometry logic lives here beyond converting canvas pixels to PDF
  points for the preview overlay.
- `signer.py` — pure geometry and stamping, no UI imports. Safe to call from tests and scripts.
- `requirements.txt` — `pymupdf` only.

Both modules use `import pymupdf as fitz`. The name `fitz` is the PyMuPDF API, but importing
the `fitz` module directly prints a deprecation warning in PyMuPDF 1.28+, so the alias is used.

## Dependencies

`pymupdf` is the only external dependency and it should stay that way.

- Do **not** add PyPDF2 or pypdf. An earlier draft of `main.py` used PyPDF2 and was replaced.
- Do **not** add Pillow. It is not needed: PyMuPDF renders a pixmap and `tk.PhotoImage` loads
  it directly (PPM for the page, PNG for the signature thumbnail so alpha survives). Tk 8.6
  supports both formats natively.

## Running and testing

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

`python main.py` opens a blocking GUI window. **Never leave it running in a test or CI step.**
To verify changes without a window:

- Import check: `.venv/bin/python -c "import signer, main; print('ok')"`
- Exercise `signer.py` directly. It has no UI dependency, so `signature_size`, `stamp_rect`,
  and `stamp_signature` can be called headlessly. Build fixtures in a temp dir with
  `fitz.open()` / `doc.new_page()` for the document and `fitz.Pixmap(...).save(...)` for a PNG.
- Verify a stamp actually landed where expected by reading `page.get_image_info()[0]["bbox"]`
  from the output and reconstructing the center.
- If the GUI itself must be tested, build `PdfSignerApp` against a `tk.Tk()` root that has been
  `withdraw()`n, drive it by calling methods directly, and never call `mainloop()`. Monkeypatch
  `main.messagebox` to keep dialogs from blocking.

## Coordinate system

This is the part that breaks most easily. Three systems are in play:

- **Canvas**: pixels, origin top-left, Y grows down.
- **PyMuPDF `Rect`**: points, origin top-left, Y grows down.
- **Stored click positions**: points, origin **bottom-left**, the classic PDF convention.

A click is converted to a stored position with:

```python
pdf_x = page.rect.x0 + canvas_x / zoom
pdf_y = page.rect.y1 - canvas_y / zoom
```

`stamp_rect` receives that bottom-left `center_y` and flips it back with
`page_rect.y0 + page_rect.y1 - center_y` before building the `fitz.Rect` that
`insert_image` and `show_pdf_page` expect. If you change one side of this conversion, change
the other and re-verify with a real stamp.

## Sizing rules

- `WIDTHS = {"S": 120.0, "M": 180.0, "L": 260.0}`, in points. UI labels map
  Pequeño/Mediano/Grande onto S/M/L.
- The click is the **center** of the signature, not a corner.
- Height comes from the signature's own aspect ratio (`width * sig_h / sig_w`). Never set
  height independently.
- If the rect overflows the page, shift it inward. If the signature is larger than the whole
  page, scale it down with a single factor applied to both dimensions so the aspect ratio
  survives. Clamping must never stretch the signature.
- Image signatures are measured at 72 dpi, so 1 px equals 1 pt. PDF signatures are measured
  from the first page's `rect`.

## Behavior to preserve

- The document opens on its **last** page, which is where signatures usually go.
- One stamp per run. A new click replaces the previous one, so the overlay is never visible
  on a page that will not be signed.
- The output must never overwrite the input; paths are compared with `realpath` + `normcase`.
- Pages other than the signed one are preserved, because the whole document is saved with
  `doc.save(output_path, deflate=True)`.
- `fitz.Document` objects are closed when switching files and on window close, so the PDF is
  not left locked.

## Packaging and releases

- Binaries are built with PyInstaller from `pdf-signer.spec` by
  `.github/workflows/release.yml`, triggered by pushing a `v*` tag. Four
  assets: `pdf-signer-windows-amd64.exe`, `pdf-signer-macos-arm64.zip`,
  `pdf-signer-macos-intel.zip`, `pdf-signer-linux-amd64`. `workflow_dispatch`
  builds the same binaries as workflow artifacts without publishing a release.
- PyInstaller is a build-time tool. Never add it to `requirements.txt`.
- `python main.py --selftest` (also supported by the frozen binaries) stamps a
  test PDF headlessly, verifies the stamped bbox, writes `selftest.log` in the
  working directory, and exits 0 or 1. It never opens a window, so it is safe
  in CI; the log exists because `--windowed` binaries have no console output.
- macOS Intel uses the `macos-15-intel` runner label (`macos-13` was retired in
  2025 and its jobs queue forever). GitHub drops x86_64 images in August 2027;
  after that, remove the Intel job.
- Keep Linux on `ubuntu-22.04` so the binary's glibc baseline stays at 2.35,
  and macOS pinned to `macos-15`/`macos-15-intel` instead of `macos-latest`
  (which migrated to macOS 26) for reproducible builds.

## Conventions

- **UI strings are in Spanish.** Error dialogs, labels and buttons included. Code identifiers
  and these agent docs are in English.
- No superfluous comments. A comment should state a constraint the code cannot show, such as
  why `except Exception` is needed for PyMuPDF write failures. Do not narrate what the next
  line does.
- Errors that a user can cause — encrypted PDF, corrupt file, signature PDF with no pages,
  unwritable destination — must raise `ValueError` from `signer.py` with a clear Spanish
  message, and `main.py` shows it in a `messagebox`.
- **Do not touch `.commandcode/`.** It is tooling configuration, not part of the app.
- Do not commit unless explicitly asked.
