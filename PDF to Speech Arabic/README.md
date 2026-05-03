# PDF Scanned to Arabic Speech

## Note 

This project was created with significant assistance from AI, guided by my direction.  
It serves as a proof of concept and has been tested on a few sample pages.  
While functional, it is not fully production-ready and may require further refinement for broader use.
> **Suggestion:** For improved results, consider using a Large Language Model (LLM) to further refine the extracted text before passing it to the text-to-speech (TTS) stage. This can help correct OCR errors and enhance the quality of the generated speech.

Converts scanned Arabic PDF files to speech (MP3) using OCR + TTS.  
Two scripts are provided — pick the one that suits your setup.

---

## Scripts

### 1. `pdf_to_speech_easyocr.py` (Recommended)

Uses **EasyOCR** — pure Python, no system dependencies needed.  
Supports **AMD GPUs** via DirectML, NVIDIA via CUDA, or CPU fallback.

#### Requirements

```bash
pip install easyocr gTTS pymupdf torch-directml
```

> `torch-directml` is optional — only needed for AMD GPU acceleration.  
> On first run, EasyOCR will automatically download the Arabic OCR model.

#### Usage

```bash
# Basic — auto-detects GPU, outputs test.mp3
python pdf_to_speech_easyocr.py test.pdf

# Save extracted text alongside audio
python pdf_to_speech_easyocr.py test.pdf --save-text

# Custom output filename
python pdf_to_speech_easyocr.py test.pdf -o output.mp3

# Force CPU (skip GPU detection)
python pdf_to_speech_easyocr.py test.pdf --cpu

# Force GPU
python pdf_to_speech_easyocr.py test.pdf --gpu
```

#### GPU Support

| GPU Brand | Backend      | Package           |
|-----------|-------------|-------------------|
| AMD       | DirectML    | `torch-directml`  |
| NVIDIA    | CUDA        | `torch` (default) |
| None      | CPU         | No extra install   |

The script auto-detects the best available device.

---

### 2. `pdf_to_speech_arabic.py` (Tesseract-based)

Uses **Tesseract OCR** — requires system installation.

#### Requirements

```bash
pip install pymupdf pytesseract gTTS Pillow
```

#### System Dependencies

1. **Tesseract OCR** with Arabic language pack:
   - **Windows**: Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki), select "Arabic" during install
   - **Linux**: `sudo apt install tesseract-ocr tesseract-ocr-ara`

#### Usage

```bash
# Basic usage
python pdf_to_speech_arabic.py test.pdf

# Save extracted text
python pdf_to_speech_arabic.py test.pdf --save-text

# Specify Tesseract path (Windows)
python pdf_to_speech_arabic.py test.pdf --tesseract "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

---

## Output Files

| Input       | Output        | Description                  |
|-------------|---------------|------------------------------|
| `test.pdf`  | `test.mp3`    | Arabic speech audio          |
| `test.pdf`  | `test.txt`    | Extracted text (with `--save-text`) |

## How It Works

1. **PDF → Images**: Each page is rendered at 300 DPI using PyMuPDF
2. **Images → Text**: OCR extracts Arabic text (EasyOCR or Tesseract)
3. **Text → Speech**: Google TTS (gTTS) converts text to Arabic audio MP3
