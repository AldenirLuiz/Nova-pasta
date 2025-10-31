from pathlib import Path
import cv2
import numpy as np

def preprocess_image(image_path):
    """
    Carrega a imagem e aplica filtros para melhorar OCR:
    - leitura segura
    - conversão para cinza
    - desruído
    - binarização adaptativa
    - pequena abertura para remover pontos
    Retorna imagem pronta para pytesseract.
    """
    p = Path(image_path)
    if not p.exists():
        raise FileNotFoundError(f"Imagem não encontrada: {p}")

    img = cv2.imread(str(p), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Falha ao ler a imagem: {p}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    # adaptive threshold (invertido se marcar com X/pontos for escuro)
    thresh = cv2.adaptiveThreshold(denoised, 255,
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 5, 9)
    # opcional: remoção de ruído pequeno
    kernel = np.ones((2,2), np.uint8)
    opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    
    return thresh


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    test_image = base.parent.joinpath("../", 'img2.png')
    processed = preprocess_image(test_image)
    cv2.imshow("Processed Image", processed)
    cv2.waitKey(0)
    cv2.destroyAllWindows()