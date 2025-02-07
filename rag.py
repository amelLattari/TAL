import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import re
from transformers import BertTokenizer, BertForQuestionAnswering

# Chemins des fichiers
PDF_CHUNKS_FILE = "pdf_chunks.json"
INDEX_FILE = "sec_index.faiss"
EMBEDDINGS_FILE = "sec_embeddings.npy"

# Chargement du modèle d'encodage
model = SentenceTransformer("sentence-transformers/all-MiniLM-L12-v2")  # Modèle plus puissant
tokenizer_qa = BertTokenizer.from_pretrained('bert-large-uncased-whole-word-masking-finetuned-squad')
model_qa = BertForQuestionAnswering.from_pretrained('bert-large-uncased-whole-word-masking-finetuned-squad')

# Charger les chunks de texte des rapports SEC
def load_chunks(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Le fichier {file_path} est introuvable.")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Prétraitement des textes (nettoyage basique)
def preprocess_text(text):
    return text.replace("\n", " ").strip()

# Extraction améliorée de "net income" via regex
def extract_net_income(text):
    match = re.search(r'(net\s*income|net\s*profit).*?(\$\d+[\.,]?\d*)', text, re.IGNORECASE)
    if match:
        return match.group(2)  # Retourne la valeur capturée
    return "Net income not found"

# Création de l'index FAISS avec IVF et PQ (quantification des produits)
def build_index(chunks):
    texts = [preprocess_text(chunk["chunk_text"]) for chunk in chunks]

    print("🔄 Encodage des textes...")
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)

    print("📌 Création de l'index FAISS avec IVF et PQ...")
    dimension = embeddings.shape[1]
    nlist = 100  # Nombre de clusters pour IVF
    nbits = 8  # Nombre de bits pour la quantification des produits

    quantizer = faiss.IndexFlatL2(dimension)  # Quantizer utilisé pour l'index IVF
    index = faiss.IndexIVFPQ(quantizer, dimension, nlist, nbits, faiss.METRIC_L2)

    print("🧠 Entraînement de l'index FAISS...")
    index.train(embeddings)  # Entraînement sur les embeddings
    index.add(embeddings)    # Ajout des embeddings à l'index

    print("💾 Sauvegarde des embeddings et de l'index...")
    np.save(EMBEDDINGS_FILE, embeddings)
    faiss.write_index(index, INDEX_FILE)

    return index, texts

# Charger ou créer l'index
def load_or_create_index():
    if os.path.exists(INDEX_FILE) and os.path.exists(PDF_CHUNKS_FILE):
        try:
            print("✅ Chargement de l'index existant...")
            index = faiss.read_index(INDEX_FILE)
            texts = [preprocess_text(chunk["chunk_text"]) for chunk in load_chunks(PDF_CHUNKS_FILE)]
            return index, texts
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement de l'index : {e}")

    print("🚀 Index non trouvé, création en cours...")
    chunks = load_chunks(PDF_CHUNKS_FILE)
    return build_index(chunks)

# Recherche de documents pertinents
def search_documents(query, top_k=3):
    index, texts = load_or_create_index()

    print(f"\n🔎 Recherche : {query}")

    # Reformulation de la question pour améliorer la recherche
    query_embedding = model.encode([query], convert_to_numpy=True)

    # Recherche dans l'index FAISS
    index.nprobe = 10  # Nombre de clusters explorés lors de la recherche (peut être ajusté)
    distances, indices = index.search(query_embedding, top_k)

    results = [{"score": distances[0][i], "text": texts[indices[0][i]], "net_income": extract_net_income(texts[indices[0][i]])} for i in range(len(indices[0]))]

    return results

# Interface interactive
if __name__ == "__main__":
    while True:
        query = input("\n📝 Posez une question sur les rapports SEC (ou 'exit' pour quitter) : ")
        if query.lower() == "exit":
            break

        results = search_documents(query)

        print("\n🔍 Résultats pertinents :\n")
        for idx, res in enumerate(results):
            print(f"{idx+1}. (Score: {res['score']:.4f}) {res['net_income']} - {res['text']}\n{'-'*50}")