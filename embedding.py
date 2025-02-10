# precompute_embeddings.py
import zipfile
import PyPDF2
import json
import numpy as np
from io import BytesIO
from sentence_transformers import SentenceTransformer

def load_pdf(file_obj):
    """Extract text content from a PDF file."""
    reader = PyPDF2.PdfReader(file_obj)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def load_and_chunk_pdfs_from_zip(zip_path):
    """Extract and split text from all PDF files in a ZIP archive."""
    all_chunks = []
    with zipfile.ZipFile(zip_path, 'r') as archive:
        pdf_files = [name for name in archive.namelist() if name.endswith(".pdf")]
        for pdf_name in pdf_files:
            # Read the PDF file as binary data and wrap it with BytesIO
            with archive.open(pdf_name) as pdf_file:
                file_bytes = pdf_file.read()
                pdf_io = BytesIO(file_bytes)
                text = load_pdf(pdf_io)
                chunks = chunk_text(text)
                all_chunks.extend(chunks)
    return all_chunks

def main():
    zip_path = "Pds.zip"  # Chemin vers l'archive ZIP contenant les PDF
    output_file = "embedding_data.json"
    
    # Extraction et découpage des PDF
    chunks = load_and_chunk_pdfs_from_zip(zip_path)
    
    # Chargement du modèle d'embedding
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Calcul des embeddings pour chaque chunk
    embeddings = model.encode(chunks)
    
    # Convertir les embeddings en liste pour pouvoir les sérialiser en JSON
    embeddings_list = embeddings.tolist()
    
    # Préparer les données à sauvegarder
    data = {
        "chunks": chunks,
        "embeddings": embeddings_list
    }
    
    # Sauvegarder dans un fichier JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
    
    print(f"Saved {len(chunks)} chunks and embeddings to {output_file}")

if __name__ == '__main__':
    main()
