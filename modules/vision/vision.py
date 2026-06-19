import cv2
import easyocr
from .detect_text_areas import extract_words_from_image

class OCRModule:
    def __init__(self, mode: str = 'default'):
        self.language = 'es'
        self.reader = easyocr.Reader([self.language])
        self.mode = mode

    def analyze_image_default(self, image_path: str):
        image = cv2.imread(image_path)
        results = self.reader.readtext(image)
        return results
    
    def analyze_image_custom(self, image_path: str):
        words = extract_words_from_image(image_path)
        # TODO: Add OCR with the custom model
        return words

    def ocr_module(self, image_path):
        if self.mode == "default":
            return self.analyze_image_default(image_path)
        elif self.mode == "custom":
            return self.analyze_image_custom(image_path)
        else:
            raise ValueError(f"Invalid mode: {self.mode}. Only 'default' and 'custom' modes are supported.")