import sys
import pytesseract
from pathlib import Path
from preprocessor import preprocess_image
from parser import parse_attendance_data
from reporter import generate_report

def main(image_path: str = None):
    # Setup paths and Tesseract
    base = Path(__file__).resolve().parent
    default_image = base.parent.joinpath('../', 'BEST.png')
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

    # Configure Tesseract for table-like content
    config = '--psm 6 --oem 3 -c preserve_interword_spaces=1'
    text = pytesseract.image_to_string(proc, lang='por+eng', config=config)
    
    # Parse attendance data
    attendance_data = parse_attendance_data(text)
    
    # Generate and save report
    generate_report(attendance_data)

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(arg)