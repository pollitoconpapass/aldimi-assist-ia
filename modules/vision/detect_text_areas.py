import os
import cv2

def extract_words_from_image(image_path, output_dir="tmp"):
    os.makedirs(output_dir, exist_ok=True)

    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not load image at {image_path}")
        return
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0) # -> desenfoque gaussiano reduce el ruido, lo que evita que Canny detecte demasiados bordes falsos

    # Canny: 
    edges = cv2.Canny(blurred, 50, 150)

    # Dilatacion
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
    dilated = cv2.dilate(edges, kernel, iterations=1)
    closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel)

    # Hallar contornos
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Ordenar contornos
    def sort_contours(cnts):
        bounding_boxes = [cv2.boundingRect(c) for c in cnts]
        (cnts, bounding_boxes) = zip(*sorted(zip(cnts, bounding_boxes),
                                             key=lambda b: (b[1][1], b[1][0]))) # Sort by Y, then X
        return cnts

    contours = sort_contours(contours)

    word_count = 0
    valid_word_imgs = []

    # Filtrar contornos
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
    
        aspect_ratio = float(w) / h if h > 0 else 0 # -> aspect ratio = width / height

        # Filtra el ruido (demasiado pequeño), los bloques enormes (demasiado grandes) o los caracteres individuales (relación de aspecto demasiado baja).
        if 100 < area < 15000 and 1.2 < aspect_ratio < 15.0:
            
            padding = 2 # -> pequeño margen al recorte para que las letras no se corten en los bordes.
            x_start = max(0, x - padding)
            y_start = max(0, y - padding)
            x_end = min(img.shape[1], x + w + padding)
            y_end = min(img.shape[0], y + h + padding)

            # Recortar la palabra
            word_img = img[y_start:y_end, x_start:x_end]
            
            # Guardar la palabra
            filename = f"word_{word_count:04d}.png"
            save_path = os.path.join(output_dir, filename)
            cv2.imwrite(save_path, word_img)
            valid_word_imgs.append(word_img)
            

    print(f"Successfully extracted {word_count} words to '{output_dir}'")
    return valid_word_imgs