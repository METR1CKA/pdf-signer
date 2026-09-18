# PDF Signer

Aplicación de escritorio para colocar un sello visual de firma sobre un documento PDF.
Eliges el PDF, eliges la firma, haces click en la página donde quieres que vaya y guardas
una copia firmada. No hace falta saber coordenadas.

**No es una firma digital.** No genera PAdES, no usa certificados y no acredita identidad
ni integridad del documento. Es una imagen estampada sobre la página, igual que pegar un
sello de tinta en un papel: cualquiera puede extraerla o taparla en el PDF resultante.

## Requisitos

- Python 3.10 o superior
- tkinter (viene con la biblioteca estándar; en algunas distribuciones de Linux se instala
  aparte como `python3-tk`)
- pymupdf (única dependencia externa)

## Instalación y ejecución

```bash
cd "/Volumes/SSD EXTERNO/DEV-PROJECTS/repos/my-projects/pdf-signer"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

En sesiones posteriores basta con activar el entorno y ejecutar la app:

```bash
source .venv/bin/activate
python main.py
```

## Uso

1. **Documento.** Elige el PDF que quieres firmar. Se abre en la última página, que es donde
   normalmente va la firma, y el destino se propone como `nombre_firmado.pdf` junto al original.
2. **Firma.** Elige un PNG, JPG o JPEG (se respeta la transparencia) o un PDF, del que se usa
   su primera página.
3. **Página.** Navega con los botones ◀ y ▶ si la firma va en otra página.
4. **Click.** Haz click sobre el preview en el punto donde quieres el centro de la firma.
   Aparece un recuadro con la miniatura real de la firma, así ves cómo va a quedar antes de
   guardar. Si haces click en otro sitio, la firma se mueve ahí.
5. **Tamaño.** Pequeño, Mediano o Grande (120, 180 o 260 puntos de ancho). El alto se calcula
   a partir de la proporción de tu firma, nunca se deforma. Si el recuadro se sale del borde
   de la página, se desplaza hacia adentro automáticamente.
6. **Guardar en.** Opcional, solo si quieres cambiar el destino propuesto.
7. **Firmar.** El botón se habilita cuando ya hay documento, firma, posición y destino. Al
   terminar puedes abrir la carpeta donde quedó el archivo.

El documento original nunca se modifica: la app rechaza guardar encima de él y las páginas
que no llevan firma se copian tal cual.

## Limitaciones

- Una estampa por corrida. Se firma la página del click activo; un click nuevo reemplaza al
  anterior. Para firmar varias páginas, repite el proceso sobre el archivo ya firmado.
- De una firma en PDF solo se usa la primera página.
- La posición se fija con un click y el tamaño con el selector: no se puede arrastrar el
  recuadro ni rotar la firma.
- El zoom del preview se calcula para que la página quepa (máximo 2x); no es ajustable.
- Los PDF protegidos con contraseña se rechazan, no se pide la contraseña.

## Estructura

| Archivo | Contenido |
|---|---|
| `main.py` | Interfaz tkinter, preview y orquestación. |
| `signer.py` | Cálculo de la geometría del sello y estampado con PyMuPDF. Sin interfaz. |
| `requirements.txt` | La única dependencia, `pymupdf`. |
