import fitz  # PyMuPDF
import os
import json
import re
from collections import Counter

INPUT_DIR = "input"  # Updated for Docker compatibility
OUTPUT_DIR = "output"  # Updated for Docker compatibility


def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()


def extract_spans_from_page(page, height_thresholds=(0.1, 0.9)):
    page_height = page.rect.height
    spans = []
    blocks = page.get_text("dict")["blocks"]
    
    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = clean_text(span.get("text", ""))
                if not text:
                    continue
                
                top_y = span["bbox"][1]
                if not (height_thresholds[0] * page_height <= top_y <= height_thresholds[1] * page_height):
                    continue
                
                spans.append({
                    "text": text,
                    "size": round(span["size"], 1),
                    "page": page.number
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


def assign_font_to_heading_levels(font_groups):
    font_to_level = {}
    
    for i, group in enumerate(font_groups):
        level = f"H{i+1}" if i < 4 else None
        if level:
            for size in group:
                font_to_level[size] = level
    
    return font_to_level


def extract_outline(pdf_path):
    doc = fitz.open(pdf_path)
    all_spans = []
    
    for page in doc:
        all_spans.extend(extract_spans_from_page(page))
    
    all_font_sizes = [span["size"] for span in all_spans]
    grouped_sizes = group_font_sizes_by_tolerance(all_font_sizes)
    font_to_level = assign_font_to_heading_levels(grouped_sizes)
    
    outline = []
    title = None
    
    for span in all_spans:
        level = font_to_level.get(span["size"])
        if level:
            outline.append({
                "level": level,
                "text": span["text"],
                "page": span["page"]
            })
            
            if not title and span["page"] == 0 and level == "H1":
                title = span["text"]
    
    if not title:
        # Fallback: find largest font on page 1
        page_1_spans = [s for s in all_spans if s["page"] == 0]
        if page_1_spans:
            title = max(page_1_spans, key=lambda s: s["size"])["text"]
    
    doc.close()  # Good practice to close the document
    
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
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✔ Processed {filename}")
        except Exception as e:
            print(f"✖ Failed to process {filename}: {e}")


if __name__ == "__main__":
    main()