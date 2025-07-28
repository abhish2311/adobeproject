import fitz  # PyMuPDF
import os
import json
import re
from collections import Counter
import unicodedata

INPUT_DIR = "input"
OUTPUT_DIR = "output"

def detect_language_script(text):
    """Detect the script/language family of text"""
    if not text:
        return "latin"
    
    # Count characters by Unicode blocks
    script_counts = {
        'latin': 0,
        'cjk': 0,  # Chinese, Japanese, Korean
        'arabic': 0,
        'devanagari': 0,  # Hindi
        'cyrillic': 0
    }
    
    for char in text:
        # Get Unicode category and name
        try:
            unicode_name = unicodedata.name(char, '')
            
            # CJK characters (Chinese, Japanese, Korean)
            if ('\u4e00' <= char <= '\u9fff' or  # CJK Unified Ideographs
                '\u3040' <= char <= '\u309f' or  # Hiragana
                '\u30a0' <= char <= '\u30ff' or  # Katakana
                '\uac00' <= char <= '\ud7af'):   # Hangul
                script_counts['cjk'] += 1
            
            # Arabic script
            elif '\u0600' <= char <= '\u06ff' or '\u0750' <= char <= '\u077f':
                script_counts['arabic'] += 1
            
            # Devanagari (Hindi)
            elif '\u0900' <= char <= '\u097f':
                script_counts['devanagari'] += 1
            
            # Cyrillic
            elif '\u0400' <= char <= '\u04ff':
                script_counts['cyrillic'] += 1
            
            # Latin (default for most European languages)
            elif char.isalpha():
                script_counts['latin'] += 1
        except:
            continue
    
    # Return the script with highest count
    return max(script_counts, key=script_counts.get)

def clean_text(text, script_type="latin"):
    """Clean text based on detected script type"""
    if not text:
        return ""
    
    if script_type == "cjk":
        # For CJK languages, preserve spacing differently
        # Remove excessive whitespace but be more careful with CJK punctuation
        text = re.sub(r'\s+', ' ', text)
        # Remove spaces around CJK characters if they seem unnecessary
        text = re.sub(r'(?<=[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff])\s+(?=[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff])', '', text)
    elif script_type == "arabic":
        # Arabic text flows right-to-left, handle spacing carefully
        text = re.sub(r'\s+', ' ', text)
        # Remove extra spaces around Arabic punctuation
        text = re.sub(r'\s*([،؛؟])\s*', r'\1 ', text)
    else:
        # Default cleaning for Latin and other scripts
        text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def is_likely_heading(text, font_size, avg_font_size, script_type="latin"):
    """Enhanced heading detection considering multilingual aspects"""
    if not text or len(text.strip()) == 0:
        return False
    
    # Basic font size check
    if font_size <= avg_font_size:
        return False
    
    # Script-specific heading patterns
    if script_type == "cjk":
        # CJK headings often have specific patterns
        # Check for chapter markers, numbering patterns
        cjk_heading_patterns = [
            r'^第[一二三四五六七八九十\d]+章',  # Chapter in Chinese/Japanese
            r'^第[一二三四五六七八九十\d]+節',  # Section
            r'^\d+[\.\s]',  # Numbered sections
            r'^[一二三四五六七八九十]+[\.\s]',  # Chinese numerals
        ]
        if any(re.match(pattern, text) for pattern in cjk_heading_patterns):
            return True
    
    elif script_type == "arabic":
        # Arabic heading patterns
        arabic_heading_patterns = [
            r'^الفصل\s+[\d]+',  # Chapter
            r'^الباب\s+[\d]+',  # Section
            r'^\d+[\.\s]',  # Numbered
        ]
        if any(re.match(pattern, text) for pattern in arabic_heading_patterns):
            return True
    
    elif script_type == "devanagari":
        # Hindi heading patterns
        hindi_heading_patterns = [
            r'^अध्याय\s+[\d]+',  # Chapter
            r'^भाग\s+[\d]+',     # Part
            r'^\d+[\.\s]',       # Numbered
        ]
        if any(re.match(pattern, text) for pattern in hindi_heading_patterns):
            return True
    
    # Common patterns across scripts
    common_patterns = [
        r'^\d+[\.\s]',  # 1. or 1 
        r'^[A-Z][a-z]*\s+\d+',  # Chapter 1, Section 2, etc.
        r'^[IVX]+[\.\s]',  # Roman numerals
    ]
    
    if any(re.match(pattern, text) for pattern in common_patterns):
        return True
    
    # Length-based filtering (adjust for different scripts)
    max_heading_length = 200 if script_type == "cjk" else 150
    if len(text) > max_heading_length:
        return False
    
    return True

def extract_spans_from_page(page, height_thresholds=(0.1, 0.9)):
    page_height = page.rect.height
    spans = []
    blocks = page.get_text("dict")["blocks"]
    
    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text:
                    continue
                
                # Detect script type for this span
                script_type = detect_language_script(text)
                cleaned_text = clean_text(text, script_type)
                
                if not cleaned_text:
                    continue
                
                top_y = span["bbox"][1]
                if not (height_thresholds[0] * page_height <= top_y <= height_thresholds[1] * page_height):
                    continue
                
                spans.append({
                    "text": cleaned_text,
                    "size": round(span["size"], 1),
                    "page": page.number,
                    "script_type": script_type,
                    "font": span.get("font", ""),
                    "flags": span.get("flags", 0)  # Font style flags
                })
    
    return spans

def group_font_sizes_by_tolerance(sizes, tolerance=0.5):
    sorted_sizes = sorted(set(sizes), reverse=True)
    grouped = []
    
    for size in sorted_sizes:
        if not grouped or abs(grouped[-1][0] - size) > tolerance:
            grouped.append([size])
        else:
            grouped[-1].append(size)
    
    return grouped

def assign_font_to_heading_levels(font_groups, spans):
    font_to_level = {}
    
    # Calculate average font size for heading detection
    avg_font_size = sum(span["size"] for span in spans) / len(spans) if spans else 12
    
    for i, group in enumerate(font_groups):
        level = f"H{i+1}" if i < 4 else None
        if level:
            for size in group:
                font_to_level[size] = level
    
    return font_to_level, avg_font_size

def extract_outline(pdf_path):
    doc = fitz.open(pdf_path)
    all_spans = []
    
    for page in doc:
        all_spans.extend(extract_spans_from_page(page))
    
    if not all_spans:
        doc.close()
        return {"title": "Untitled", "outline": []}
    
    all_font_sizes = [span["size"] for span in all_spans]
    grouped_sizes = group_font_sizes_by_tolerance(all_font_sizes)
    font_to_level, avg_font_size = assign_font_to_heading_levels(grouped_sizes, all_spans)
    
    outline = []
    title = None
    
    for span in all_spans:
        level = font_to_level.get(span["size"])
        if level and is_likely_heading(span["text"], span["size"], avg_font_size, span["script_type"]):
            outline.append({
                "level": level,
                "text": span["text"],
                "page": span["page"] + 1  # Convert to 1-based page numbering
            })
            
            # Try to find title from first page, largest font
            if not title and span["page"] == 0 and level == "H1":
                title = span["text"]
    
    # Fallback title detection
    if not title:
        page_1_spans = [s for s in all_spans if s["page"] == 0]
        if page_1_spans:
            # Find the largest font on page 1 that looks like a title
            title_candidate = max(page_1_spans, key=lambda s: s["size"])
            title = title_candidate["text"]
    
    doc.close()
    
    return {
        "title": title or "Untitled",
        "outline": outline
    }

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    pdf_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        print("No PDF files found in input directory")
        return
    
    for filename in pdf_files:
        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename.replace(".pdf", ".json"))
        
        try:
            data = extract_outline(input_path)
            # Use ensure_ascii=False to properly handle non-ASCII characters
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✔ Processed {filename}")
        except Exception as e:
            print(f"✖ Failed to process {filename}: {e}")

if __name__ == "__main__":
    main()
