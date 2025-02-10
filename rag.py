import zipfile
import os
import PyPDF2
import numpy as np
import faiss
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer

# Charger le modèle d'embedding
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def load_pdf(file_obj):
    """Charge le contenu texte d'un fichier PDF."""
    reader = PyPDF2.PdfReader(file_obj)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return text


def chunk_text(text, chunk_size=500, overlap=50):
    """Divise le texte en segments avec chevauchement."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks


def load_and_chunk_pdfs_from_zip(zip_path):
    """Charge et segmente les textes des fichiers PDF contenus dans une archive ZIP."""
    all_chunks = []
    with zipfile.ZipFile(zip_path, 'r') as archive:
        pdf_files = [name for name in archive.namelist() if name.endswith(".pdf")]
        for pdf_name in pdf_files:
            with archive.open(pdf_name, mode='r') as pdf_file:  # Assurez-vous que c'est en mode binaire
                text = load_pdf(pdf_file)
                chunks = chunk_text(text)
                all_chunks.extend(chunks)
    return all_chunks


def create_embeddings(chunks):
    """Crée les embeddings pour les segments de texte."""
    chunk_embeddings = embedding_model.encode(chunks)
    return np.array(chunk_embeddings).astype('float32')


def create_faiss_index(embeddings):
    """Crée un index FAISS pour les embeddings."""
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index


# Charger le modèle GPT pour la génération de texte
model_name = "EleutherAI/gpt-neo-2.7B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

def generate_response(query, index, chunks, model, tokenizer, top_k=5):
    """Génère une réponse à partir des chunks pertinents."""
    query_embedding = embedding_model.encode([query])
    distances, indices = index.search(query_embedding, top_k)
    relevant_chunks = [chunks[i] for i in indices[0]]
    context = " ".join(relevant_chunks)
    if len(context.split()) > 1024:
        context = " ".join(context.split()[:1024])
    input_text = f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"
    inputs = tokenizer(input_text, return_tensors="pt", truncation=True)
    outputs = model.generate(**inputs, max_new_tokens=200)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response


def search_documents_from_zip(zip_path, query):
    """Rechercher dans les documents d'une archive ZIP."""
    # Charger et segmenter les rapports PDF
    chunks = load_and_chunk_pdfs_from_zip(zip_path)
    
    # Créer les embeddings des chunks
    chunk_embeddings = create_embeddings(chunks)
    
    # Créer l'index FAISS
    index = create_faiss_index(chunk_embeddings)
    
    # Générer une réponse à la question
    response = generate_response(query, index, chunks, model, tokenizer)
    
    return response


