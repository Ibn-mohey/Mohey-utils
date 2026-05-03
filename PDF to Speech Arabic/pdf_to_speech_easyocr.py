"""
PDF Scanned to Arabic Speech Converter (EasyOCR version)
No system dependencies needed - pure Python.
Supports AMD GPUs via DirectML.

Requirements:
    pip install easyocr gTTS pymupdf torch-directml
"""

import sys
import argparse
from pathlib import Path

import fitz  # PyMuPDF
import easyocr
from gtts import gTTS


def get_device():
    """Detect best available device: AMD (DirectML) > CUDA > CPU."""
    try:
        import torch_directml
        device = torch_directml.device()
        print("🎮 Using AMD GPU (DirectML)")
        return True  # EasyOCR uses gpu=True/False
    except ImportError:
        pass
    
    import torch
    if torch.cuda.is_available():
        print("🎮 Using NVIDIA GPU (CUDA)")
        return True
    
    print("💻 Using CPU")
    return False


def extract_text_from_pdf(pdf_path: str, use_gpu: bool = None) -> str:
    """Extract Arabic text from a scanned PDF using EasyOCR."""
    print("📄 Opening PDF...")
    doc = fitz.open(pdf_path)
    print(f"   Found {len(doc)} page(s)")

    if use_gpu is None:
        use_gpu = get_device()

    print("🤖 Loading EasyOCR model (first run downloads the model)...")
    reader = easyocr.Reader(["ar"], gpu=use_gpu)

    full_text = []
    for i, page in enumerate(doc, 1):
        print(f"🔍 OCR processing page {i}/{len(doc)}...")
        pix = page.get_pixmap(dpi=300)
        img_bytes = pix.tobytes("png")
        results = reader.readtext(img_bytes, detail=0, paragraph=True)
        page_text = "\n".join(results).strip()
        if page_text:
            full_text.append(page_text)

    combined = "\n\n".join(full_text)
    print(f"✅ Extracted {len(combined)} characters of text")
    return combined


def text_to_speech(text: str, output_path: str) -> None:
    """Convert Arabic text to speech and save as MP3."""
    print("🔊 Generating speech...")
    tts = gTTS(text=text, lang="ar")
    tts.save(output_path)
    print(f"✅ Audio saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert scanned Arabic PDF to speech (EasyOCR)")
    parser.add_argument("pdf", help="Path to the scanned PDF file")
    parser.add_argument("-o", "--output", help="Output MP3 file path (default: same name as PDF)")
    parser.add_argument("--save-text", action="store_true", help="Also save extracted text to a .txt file")
    parser.add_argument("--gpu", action="store_true", help="Force GPU usage")
    parser.add_argument("--cpu", action="store_true", help="Force CPU usage")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)

    output_path = args.output or str(pdf_path.with_suffix(".mp3"))

    use_gpu = None  # auto-detect
    if args.cpu:
        use_gpu = False
    elif args.gpu:
        use_gpu = True

    text = extract_text_from_pdf(str(pdf_path), use_gpu=use_gpu)

    if not text.strip():
        print("❌ No text was extracted from the PDF.")
        sys.exit(1)

    if args.save_text:
        txt_path = str(pdf_path.with_suffix(".txt"))
        Path(txt_path).write_text(text, encoding="utf-8")
        print(f"📝 Text saved to: {txt_path}")

    text_to_speech(text, output_path)


if __name__ == "__main__":
    main()
