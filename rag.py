import json
import re
import numpy as np
import faiss
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer

def load_embedding_data(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    chunks = data["chunks"]
    embeddings = np.array(data["embeddings"]).astype("float32")
    return chunks, embeddings

# Création de l'index FAISS pour rechercher rapidement dans les embeddings.
def create_faiss_index(embeddings):
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index

def generate_response(query, index, chunks, model, tokenizer, embedding_model, top_k=3):
    """
    Generate a concise final answer based on relevant passages.
    If the generated answer is empty, return a message asking to rephrase the query.
    The answer will not include the question.
    """
    # Encodage de la requête et recherche des chunks pertinents
    query_embedding = embedding_model.encode([query])
    distances, indices = index.search(query_embedding, top_k)
    relevant_chunks = [chunks[i] for i in indices[0]]
    context = " ".join(relevant_chunks)
    if len(context.split()) > 1024:
        context = " ".join(context.split()[:1024])
    
    # Construction du prompt pour le modèle de génération
    prompt = (
        "You are an expert financial analyst analyzing SEC reports. "
        "You are provided with a context below extracted from SEC filings. "
        "The answer must be based strictly on the context provided. "
        "Do not repeat the question in your answer under any circumstances. "
        "Your answer must start with 'Final Answer:'.\n\n"
        f"Context: {context}\n\n"
        f"Question: {query}\n\n"
        "Final Answer:"
    )
    
    # Génération de la réponse
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True)
    outputs = model.generate(**inputs, max_new_tokens=100)
    full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Extraction de la réponse finale
    marker = "Final Answer:"
    if marker in full_output:
        final_answer = full_output.split(marker)[-1].strip()
        # Supprimer la question si elle est incluse dans la réponse
        final_answer = final_answer.replace(query, "").strip()
        # Supprimer tout ce qui suit et inclut "question:" s'il existe
        if "question:" in final_answer.lower():
            final_answer = final_answer.lower().split("question:")[0].strip()

        # Supprimer les espaces en trop et caractères résiduels
        final_answer = final_answer.rstrip(".")
        # Retourner un message si la réponse est vide
        if not final_answer:
            return "Je n'ai pas compris votre demande. Pouvez-vous reformuler votre question ?"
        return final_answer
# Initialisation des composants et des modèles
json_file = "embedding_data.json"           
model_name = "EleutherAI/gpt-neo-2.7B"
embedding_model_name = "all-MiniLM-L6-v2"

chunks, embeddings = load_embedding_data(json_file)
index = create_faiss_index(embeddings)
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)
embedding_model = SentenceTransformer(embedding_model_name)

def search(query):
    """
    Exécute une recherche et renvoie uniquement la réponse synthétisée.
    Si aucune information pertinente n'est trouvée, renvoie "Les informations ne sont pas disponibles."
    """
    return generate_response(query, index, chunks, model, tokenizer, embedding_model)
