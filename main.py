"""PDF Signer: coloca un sello visual de firma sobre un PDF con un click."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pymupdf as fitz

from signer import is_image, open_pdf, signature_size, stamp_rect, stamp_signature

SIZE_OPTIONS = {"Pequeño": "S", "Mediano": "M", "Grande": "L"}
DEFAULT_SIZE_LABEL = "Mediano"

PREVIEW_WIDTH = 620
PREVIEW_HEIGHT = 660
MAX_ZOOM = 2.0
PLACEHOLDER_RATIO = 0.4

PDF_FILETYPES = [("Documentos PDF", "*.pdf")]
SIGNATURE_FILETYPES = [
    ("Firma (imagen o PDF)", "*.png *.jpg *.jpeg *.pdf"),
    ("Imágenes", "*.png *.jpg *.jpeg"),
    ("Documentos PDF", "*.pdf"),
]


def reveal_in_file_manager(path: str) -> None:
    folder = os.path.dirname(os.path.abspath(path))
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", path], check=False)
        elif os.name == "nt":
            os.startfile(folder)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", folder], check=False)
    except Exception:
        messagebox.showinfo("Carpeta", f"El archivo está en:\n{folder}")


class PdfSignerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF Signer")
        self.root.geometry("960x720")
        self.root.minsize(860, 600)

        self.document: fitz.Document | None = None
        self.document_path: str | None = None
        self.signature_path: str | None = None
        self.output_path: str | None = None

        self.page_index = 0
        self.zoom = 1.0
        self.signature_width = 0.0
        self.signature_height = 0.0

        self.clicks: dict[int, tuple[float, float]] = {}
        self.last_placed_page: int | None = None

        self.page_photo: tk.PhotoImage | None = None
        self.signature_photo: tk.PhotoImage | None = None

        self._build_layout()
        self._update_sign_state()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # Construcción de la interfaz

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=10)
        container.pack(fill="both", expand=True)

        controls = ttk.Frame(container, width=280)
        controls.pack(side="left", fill="y")
        controls.pack_propagate(False)

        preview = ttk.Frame(container)
        preview.pack(side="left", fill="both", expand=True, padx=(12, 0))

        self._build_controls(controls)
        self._build_preview(preview)

    def _build_controls(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="PDF Signer", font=("TkDefaultFont", 15, "bold")).pack(anchor="w")
        ttk.Label(parent, text="Sello visual de firma", foreground="#666").pack(anchor="w", pady=(0, 12))

        document_box = ttk.LabelFrame(parent, text="1. Documento", padding=8)
        document_box.pack(fill="x", pady=4)
        ttk.Button(document_box, text="Elegir PDF…", command=self.choose_document).pack(fill="x")
        self.document_label = ttk.Label(document_box, text="Sin documento", wraplength=240, foreground="#666")
        self.document_label.pack(anchor="w", pady=(6, 0))

        signature_box = ttk.LabelFrame(parent, text="2. Firma", padding=8)
        signature_box.pack(fill="x", pady=4)
        ttk.Button(signature_box, text="Elegir firma…", command=self.choose_signature).pack(fill="x")
        self.signature_label = ttk.Label(signature_box, text="Sin firma", wraplength=240, foreground="#666")
        self.signature_label.pack(anchor="w", pady=(6, 0))

        page_box = ttk.LabelFrame(parent, text="3. Página", padding=8)
        page_box.pack(fill="x", pady=4)
        navigation = ttk.Frame(page_box)
        navigation.pack(fill="x")
        self.previous_button = ttk.Button(navigation, text="◀", width=4, command=self.previous_page)
        self.previous_button.pack(side="left")
        self.page_label = ttk.Label(navigation, text="– / –", anchor="center")
        self.page_label.pack(side="left", fill="x", expand=True)
        self.next_button = ttk.Button(navigation, text="▶", width=4, command=self.next_page)
        self.next_button.pack(side="right")

        size_box = ttk.LabelFrame(parent, text="4. Tamaño de la firma", padding=8)
        size_box.pack(fill="x", pady=4)
        self.size_variable = tk.StringVar(value=DEFAULT_SIZE_LABEL)
        size_combobox = ttk.Combobox(
            size_box,
            textvariable=self.size_variable,
            values=list(SIZE_OPTIONS),
            state="readonly",
        )
        size_combobox.pack(fill="x")
        size_combobox.bind("<<ComboboxSelected>>", self.on_size_change)

        output_box = ttk.LabelFrame(parent, text="5. Guardar en", padding=8)
        output_box.pack(fill="x", pady=4)
        ttk.Button(output_box, text="Elegir destino…", command=self.choose_output).pack(fill="x")
        self.output_label = ttk.Label(output_box, text="Sin destino", wraplength=240, foreground="#666")
        self.output_label.pack(anchor="w", pady=(6, 0))

        self.sign_button = ttk.Button(parent, text="Firmar", command=self.sign)
        self.sign_button.pack(fill="x", pady=(14, 4), ipady=6)

        self.status_label = ttk.Label(parent, text="", wraplength=240, foreground="#666")
        self.status_label.pack(anchor="w", pady=(6, 0))

    def _build_preview(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Click en la página para colocar la firma").pack(anchor="w", pady=(0, 6))

        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            frame,
            width=PREVIEW_WIDTH,
            height=PREVIEW_HEIGHT,
            background="#d9d9d9",
            highlightthickness=1,
            highlightbackground="#bbb",
        )
        vertical = ttk.Scrollbar(frame, orient="vertical", command=self.canvas.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.canvas.bind("<Button-1>", self.on_canvas_click)

    # Selección de archivos

    def choose_document(self) -> None:
        path = filedialog.askopenfilename(title="Elegir documento PDF", filetypes=PDF_FILETYPES)
        if not path:
            return

        try:
            document = open_pdf(path)
            if document.page_count == 0:
                document.close()
                raise ValueError("El documento no contiene páginas.")
        except ValueError as error:
            messagebox.showerror("No se pudo abrir el documento", str(error))
            return

        self.close_document()
        self.document = document
        self.document_path = path
        self.clicks.clear()
        self.last_placed_page = None
        self.page_index = document.page_count - 1

        self.document_label.configure(text=os.path.basename(path), foreground="#000")

        stem = os.path.splitext(os.path.basename(path))[0]
        self.output_path = os.path.join(os.path.dirname(path), f"{stem}_firmado.pdf")
        self.output_label.configure(text=os.path.basename(self.output_path), foreground="#000")

        self.render_page()
        self._update_sign_state()

    def choose_signature(self) -> None:
        path = filedialog.askopenfilename(title="Elegir firma", filetypes=SIGNATURE_FILETYPES)
        if not path:
            return

        extension = os.path.splitext(path)[1].lower()
        if not is_image(path) and extension != ".pdf":
            messagebox.showerror(
                "Firma no válida",
                "La firma debe ser una imagen PNG, JPG o JPEG, o bien un PDF.",
            )
            return

        try:
            self.signature_width, self.signature_height = signature_size(path)
        except ValueError as error:
            messagebox.showerror("No se pudo leer la firma", str(error))
            return

        self.signature_path = path
        self.signature_label.configure(text=os.path.basename(path), foreground="#000")
        self.draw_overlay()
        self._update_sign_state()

    def choose_output(self) -> None:
        initial_directory = os.path.dirname(self.output_path or self.document_path or "") or None
        initial_file = os.path.basename(self.output_path) if self.output_path else "firmado.pdf"

        path = filedialog.asksaveasfilename(
            title="Guardar documento firmado",
            defaultextension=".pdf",
            filetypes=PDF_FILETYPES,
            initialdir=initial_directory,
            initialfile=initial_file,
        )
        if not path:
            return

        self.output_path = path
        self.output_label.configure(text=os.path.basename(path), foreground="#000")
        self._update_sign_state()

    # Navegación y preview

    def previous_page(self) -> None:
        if self.document and self.page_index > 0:
            self.page_index -= 1
            self.render_page()

    def next_page(self) -> None:
        if self.document and self.page_index < self.document.page_count - 1:
            self.page_index += 1
            self.render_page()

    def on_size_change(self, _event: object = None) -> None:
        self.draw_overlay()

    @property
    def size_key(self) -> str:
        return SIZE_OPTIONS.get(self.size_variable.get(), "M")

    @property
    def page(self) -> fitz.Page | None:
        if self.document is None:
            return None
        return self.document[self.page_index]

    def render_page(self) -> None:
        page = self.page
        if page is None:
            return

        self.zoom = min(
            PREVIEW_WIDTH / page.rect.width,
            PREVIEW_HEIGHT / page.rect.height,
            MAX_ZOOM,
        )

        pixmap = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom))
        self.page_photo = tk.PhotoImage(data=pixmap.tobytes("ppm"))

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.page_photo, tags="page")
        self.canvas.configure(scrollregion=(0, 0, pixmap.width, pixmap.height))

        self.page_label.configure(text=f"{self.page_index + 1} / {self.document.page_count}")
        self.previous_button.state(["!disabled"] if self.page_index > 0 else ["disabled"])
        last_page = self.document.page_count - 1
        self.next_button.state(["!disabled"] if self.page_index < last_page else ["disabled"])

        self.draw_overlay()

    def draw_overlay(self) -> None:
        self.canvas.delete("overlay")

        page = self.page
        point = self.clicks.get(self.page_index)
        if page is None or point is None:
            return

        center_x, center_y = point
        if self.signature_path:
            width, height = self.signature_width, self.signature_height
        else:
            width, height = 1.0, PLACEHOLDER_RATIO

        rect = stamp_rect(page.rect, center_x, center_y, width, height, self.size_key)

        x0 = (rect.x0 - page.rect.x0) * self.zoom
        y0 = (rect.y0 - page.rect.y0) * self.zoom
        x1 = (rect.x1 - page.rect.x0) * self.zoom
        y1 = (rect.y1 - page.rect.y0) * self.zoom

        if not self.signature_path:
            self.canvas.create_rectangle(
                x0, y0, x1, y1, outline="#1f6feb", width=2, dash=(5, 3), tags="overlay"
            )
            return

        self.canvas.create_rectangle(
            x0, y0, x1, y1, fill="#1f6feb", stipple="gray12", outline="", tags="overlay"
        )

        self.signature_photo = self._render_signature(round(x1 - x0), round(y1 - y0))
        if self.signature_photo is not None:
            self.canvas.create_image(
                x0, y0, anchor="nw", image=self.signature_photo, tags="overlay"
            )

        self.canvas.create_rectangle(x0, y0, x1, y1, outline="#1f6feb", width=2, tags="overlay")

    def _render_signature(self, width_px: int, height_px: int) -> tk.PhotoImage | None:
        if not self.signature_path or width_px < 1 or height_px < 1:
            return None

        document = None
        try:
            document = fitz.open(self.signature_path)
            page = document[0]
            matrix = fitz.Matrix(width_px / page.rect.width, height_px / page.rect.height)
            pixmap = page.get_pixmap(matrix=matrix, alpha=True)
            return tk.PhotoImage(data=pixmap.tobytes("png"))
        except Exception:
            return None
        finally:
            if document is not None:
                document.close()

    def on_canvas_click(self, event: tk.Event) -> None:
        page = self.page
        if page is None:
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        if not (0 <= canvas_x <= page.rect.width * self.zoom):
            return
        if not (0 <= canvas_y <= page.rect.height * self.zoom):
            return

        pdf_x = page.rect.x0 + canvas_x / self.zoom
        pdf_y = page.rect.y1 - canvas_y / self.zoom

        # Solo se estampa un click, así que el nuevo invalida el anterior: el
        # overlay nunca queda visible en una página que no se va a firmar.
        self.clicks = {self.page_index: (pdf_x, pdf_y)}
        self.last_placed_page = self.page_index

        self.draw_overlay()
        self._update_sign_state()

    # Firmado

    def _update_sign_state(self) -> None:
        ready = bool(self.document and self.signature_path and self.clicks and self.output_path)
        self.sign_button.state(["!disabled"] if ready else ["disabled"])

        if not self.document:
            self.status_label.configure(text="Elige un documento PDF para empezar.")
        elif not self.signature_path:
            self.status_label.configure(text="Elige la imagen o el PDF de la firma.")
        elif not self.clicks:
            self.status_label.configure(text="Haz click en la página donde va la firma.")
        elif not self.output_path:
            self.status_label.configure(text="Elige dónde guardar el documento firmado.")
        else:
            page_number = (self.last_placed_page or 0) + 1
            self.status_label.configure(text=f"Listo para firmar en la página {page_number}.")

    def sign(self) -> None:
        if not (self.document and self.document_path and self.signature_path and self.output_path):
            return

        if self.last_placed_page is None or self.last_placed_page not in self.clicks:
            messagebox.showerror(
                "Falta la posición",
                "Haz click sobre la página para indicar dónde debe ir la firma.",
            )
            return

        if os.path.splitext(self.output_path)[1].lower() != ".pdf":
            messagebox.showerror("Destino no válido", "El archivo de destino debe tener extensión .pdf.")
            return

        source = os.path.normcase(os.path.realpath(self.document_path))
        destination = os.path.normcase(os.path.realpath(self.output_path))
        if source == destination:
            messagebox.showerror(
                "Destino no válido",
                "El destino no puede ser el documento original. Elige otro archivo.",
            )
            return

        center_x, center_y = self.clicks[self.last_placed_page]

        try:
            stamp_signature(
                document_path=self.document_path,
                signature_path=self.signature_path,
                output_path=self.output_path,
                page_index=self.last_placed_page,
                center_x=center_x,
                center_y=center_y,
                size=self.size_key,
            )
        except ValueError as error:
            messagebox.showerror("No se pudo firmar", str(error))
            return
        except PermissionError:
            messagebox.showerror(
                "No se pudo guardar",
                f"No hay permisos de escritura en:\n{os.path.dirname(self.output_path)}",
            )
            return
        except OSError as error:
            messagebox.showerror("No se pudo guardar", f"Error al escribir el archivo:\n{error}")
            return
        except Exception as error:
            # PyMuPDF no usa OSError: los fallos de escritura llegan como FzErrorSystem.
            messagebox.showerror(
                "No se pudo guardar",
                f"No se pudo escribir el archivo:\n{self.output_path}\n\n{error}",
            )
            return

        open_folder = messagebox.askyesno(
            "Documento firmado",
            f"Se guardó en:\n{self.output_path}\n\n¿Abrir la carpeta?",
        )
        if open_folder:
            reveal_in_file_manager(self.output_path)

    # Ciclo de vida

    def close_document(self) -> None:
        if self.document is not None:
            self.document.close()
            self.document = None

    def on_close(self) -> None:
        self.close_document()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    PdfSignerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
