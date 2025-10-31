import os
import sys
import cv2
import pytesseract
from pathlib import Path
from preprocessor import preprocess_image
from parser import parse_attendance_data
from reporter import generate_report

def main(image_path: str = None):
    base = Path(__file__).resolve().parent
    default_image = base.parent.joinpath("../", 'imagem.png')
    img_path = Path(image_path) if image_path else default_image
    pytesseract.pytesseract.tesseract_cmd = "C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"

    if not img_path.exists():
        print(f"Arquivo não encontrado: {img_path}")
        sys.exit(1)

    try:
        proc = preprocess_image(img_path)
    except Exception as e:
        print(f"Erro ao processar imagem: {e}")
        sys.exit(1)

    # Ajuste de config do tesseract se necessário (psm e idioma)
    config = '--psm 6'
    text = pytesseract.image_to_string(proc, lang='por', config=config)
    print(text)
    data = parse_attendance_data(text)
    generate_report(data)

if __name__ == "__main__":
    # aceita caminho opcional via linha de comando
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(arg)