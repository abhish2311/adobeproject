# PDF Outline Extractor - Docker Setup

This Docker setup allows you to extract outlines from PDF files using PyMuPDF.

## File Structure
```
project/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pdf_extractor.py
├── .dockerignore
├── input/          # Place your PDF files here
│   └── *.pdf
└── output/         # JSON outputs will be generated here
    └── *.json
```

## Setup Instructions

1. **Create the project structure:**
   ```bash
   mkdir pdf-extractor-docker
   cd pdf-extractor-docker
   mkdir input output
   ```

2. **Copy all the provided files** to your project directory

3. **Place your PDF files** in the `input/` directory

## Usage Options

### Option 1: Using Docker Compose (Recommended)
```bash
# Build and run
docker-compose up --build

# Run again (after first build)
docker-compose up
```

### Option 2: Using Docker directly
```bash
# Build the image
docker build -t pdf-extractor .

# Run the container
docker run -v $(pwd)/input:/app/input:ro -v $(pwd)/output:/app/output pdf-extractor
```

### Option 3: Interactive mode for debugging
```bash
# Run container interactively
docker run -it -v $(pwd)/input:/app/input:ro -v $(pwd)/output:/app/output pdf-extractor bash

# Then inside the container:
python pdf_extractor.py
```

## Output

- JSON files will be created in the `output/` directory
- Each PDF file will generate a corresponding JSON file with the same name
- The JSON contains the document title and hierarchical outline structure

## Key Features

- **Volume mounting**: Input and output directories are mounted from your host system
- **Security**: Runs as non-root user inside container
- **Error handling**: Graceful handling of processing failures
- **Clean output**: Structured JSON with extracted outline information

## Troubleshooting

- Ensure PDF files are in the `input/` directory
- Check file permissions if you encounter access issues
- View logs with `docker-compose logs` for debugging
- Make sure Docker has enough memory allocated for large PDF files

## Dependencies

- Python 3.11
- PyMuPDF (fitz) for PDF processing
- Standard libraries: os, json, re, collections