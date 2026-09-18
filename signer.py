"""Geometría y estampado de firmas visuales sobre documentos PDF."""

from __future__ import annotations

import os

import pymupdf as fitz

WIDTHS = {"S": 120.0, "M": 180.0, "L": 260.0}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def is_image(path: str) -> bool:
    """Indica si la ruta corresponde a una imagen soportada como firma."""
    return os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS


def open_pdf(path: str) -> fitz.Document:
    """Abre un PDF y lanza mensajes claros si está dañado o cifrado."""
    name = os.path.basename(path)
    try:
        document = fitz.open(path)
    except Exception as error:
        raise ValueError(
            f"No se pudo abrir «{name}»: el archivo está dañado o no es un PDF válido."
        ) from error

    if document.needs_pass:
        document.close()
        raise ValueError(f"«{name}» está cifrado y requiere contraseña para poder firmarlo.")

    return document


def signature_size(path: str) -> tuple[float, float]:
    """Ancho y alto nativos de la firma en puntos.

    Las imágenes se interpretan a 72 dpi (1 px = 1 pt); de un PDF se toma
    el rectángulo de su primera página.
    """
    name = os.path.basename(path)

    if is_image(path):
        try:
            pixmap = fitz.Pixmap(path)
        except Exception as error:
            raise ValueError(
                f"No se pudo leer la imagen de firma «{name}»: el archivo está dañado "
                "o el formato no es compatible."
            ) from error

        width, height = float(pixmap.width), float(pixmap.height)
        if width <= 0 or height <= 0:
            raise ValueError(f"La imagen de firma «{name}» no tiene dimensiones válidas.")
        return width, height

    document = open_pdf(path)
    try:
        if document.page_count == 0:
            raise ValueError(f"El PDF de firma «{name}» no contiene páginas.")
        rect = document[0].rect
        width, height = float(rect.width), float(rect.height)
        if width <= 0 or height <= 0:
            raise ValueError(f"La primera página de «{name}» no tiene dimensiones válidas.")
        return width, height
    finally:
        document.close()


def stamp_rect(
    page_rect: fitz.Rect,
    center_x: float,
    center_y: float,
    sig_w: float,
    sig_h: float,
    size: str,
) -> fitz.Rect:
    """Rectángulo de estampado centrado en (center_x, center_y).

    El centro llega en coordenadas PDF con origen abajo-izquierda y el
    rectángulo devuelto usa el sistema de PyMuPDF (origen arriba-izquierda).
    Conserva la proporción de la firma y se ajusta dentro de la página.
    """
    if sig_w <= 0 or sig_h <= 0:
        raise ValueError("Las dimensiones de la firma no son válidas.")

    if size not in WIDTHS:
        raise ValueError(f"Tamaño desconocido: {size!r}. Use 'S', 'M' o 'L'.")

    width = WIDTHS[size]
    height = width * (sig_h / sig_w)

    page_width = page_rect.x1 - page_rect.x0
    page_height = page_rect.y1 - page_rect.y0

    fit = min(1.0, page_width / width, page_height / height)
    width *= fit
    height *= fit

    center_y_top_down = page_rect.y0 + page_rect.y1 - center_y

    x0 = min(max(center_x - width / 2, page_rect.x0), page_rect.x1 - width)
    y0 = min(max(center_y_top_down - height / 2, page_rect.y0), page_rect.y1 - height)

    return fitz.Rect(x0, y0, x0 + width, y0 + height)


def stamp_signature(
    document_path: str,
    signature_path: str,
    output_path: str,
    page_index: int,
    center_x: float,
    center_y: float,
    size: str = "M",
) -> None:
    """Estampa la firma en una página y guarda el documento completo."""
    document = open_pdf(document_path)
    signature_document = None

    try:
        if not 0 <= page_index < document.page_count:
            raise ValueError(
                f"La página {page_index + 1} no existe en el documento "
                f"(tiene {document.page_count})."
            )

        page = document[page_index]
        sig_w, sig_h = signature_size(signature_path)
        rect = stamp_rect(page.rect, center_x, center_y, sig_w, sig_h, size)

        if is_image(signature_path):
            page.insert_image(rect, filename=signature_path)
        else:
            signature_document = open_pdf(signature_path)
            if signature_document.page_count == 0:
                raise ValueError(
                    f"El PDF de firma «{os.path.basename(signature_path)}» no contiene páginas."
                )
            page.show_pdf_page(rect, signature_document, 0)

        document.save(output_path, deflate=True)
    finally:
        if signature_document is not None:
            signature_document.close()
        document.close()
