"""
PDF Scanned to Arabic Speech Converter
Extracts Arabic text from scanned PDF pages using OCR, then converts to speech.

Requirements:
    pip install pymupdf pytesseract gTTS Pillow

System Requirements:
    - Tesseract OCR: https://github.com/tesseract-ocr/tesseract
      Make sure to install the Arabic language pack (ara)
"""

import sys
import argparse
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from gtts import gTTS


def extract_text_from_pdf(pdf_path: str, tesseract_cmd: str = None) -> str:
    """Extract Arabic text from a scanned PDF using OCR."""
    tesseract_cmd = tesseract_cmd or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    print(f"📄 Opening PDF...")
    doc = fitz.open(pdf_path)
    print(f"   Found {len(doc)} page(s)")

    full_text = []
    for i, page in enumerate(doc, 1):
        print(f"🔍 OCR processing page {i}/{len(doc)}...")
        # Render page to image at 300 DPI
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(img, lang="ara")
        text = text.strip()
        if text:
            full_text.append(text)

    combined = "\n\n".join(full_text)
    print(f"✅ Extracted {len(combined)} characters of text")
    return combined


def text_to_speech(text: str, output_path: str, lang: str = "ar") -> None:
    """Convert Arabic text to speech and save as MP3."""
    print(f"🔊 Generating speech...")
    tts = gTTS(text=text, lang=lang)
    tts.save(output_path)
    print(f"✅ Audio saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert scanned Arabic PDF to speech")
    parser.add_argument("pdf", help="Path to the scanned PDF file")
    parser.add_argument("-o", "--output", help="Output MP3 file path (default: same name as PDF)")
    parser.add_argument("--tesseract", help="Path to tesseract executable")
    parser.add_argument("--save-text", action="store_true", help="Also save extracted text to a .txt file")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)

    output_path = args.output or str(pdf_path.with_suffix(".mp3"))

    # Extract text
    text = extract_text_from_pdf(str(pdf_path), args.tesseract)

    if not text.strip():
        print("❌ No text was extracted from the PDF. Check that Tesseract Arabic (ara) language pack is installed.")
        sys.exit(1)

    # Optionally save text
    if args.save_text:
        txt_path = str(pdf_path.with_suffix(".txt"))
        Path(txt_path).write_text(text, encoding="utf-8")
        print(f"📝 Text saved to: {txt_path}")

    # Convert to speech
    text_to_speech(text, output_path)


if __name__ == "__main__":
    main()
