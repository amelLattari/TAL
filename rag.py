import json
import numpy as np
import faiss
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer

# Chargement des données et des embeddings
def load_embedding_data(json_file):
    """Load precomputed chunks and embeddings from a JSON file."""
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    chunks = data["chunks"]
    embeddings = np.array(data["embeddings"]).astype("float32")
    return chunks, embeddings

# Création de l'index FAISS
def create_faiss_index(embeddings):
    """Create a FAISS index from the embeddings."""
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index

# Fonction principale pour générer une réponse
def generate_response(query, index, chunks, model, tokenizer, embedding_model, top_k=3):
    """
    Generate a concise final answer based on relevant passages.
    """
    query_embedding = embedding_model.encode([query])
    distances, indices = index.search(query_embedding, top_k)
    relevant_chunks = [chunks[i] for i in indices[0]]
    context = " ".join(relevant_chunks)
    if len(context.split()) > 1024:
        context = " ".join(context.split()[:1024])
    
    prompt = (
        "You are provided with data in the context below. "
        "Ignore any existing questions and answers present in the context. "
        "Answer only the following question in one concise sentence. "
        "Do not include any context or extraneous information. "
        "Your answer must start with 'Final Answer:'.\n\n"
        f"Context: {context}\n\n"
        f"Question: {query}\n\n"
        "Final Answer:"
    )
    
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True)
    outputs = model.generate(**inputs, max_new_tokens=100)
    full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    marker = "Final Answer:"
    return full_output.split(marker)[-1].strip() if marker in full_output else full_output.strip()

# Initialisation des composants
json_file = "embedding_data.json"
model_name = "EleutherAI/gpt-neo-2.7B"
embedding_model_name = "all-MiniLM-L6-v2"

# Chargement des données et modèles
chunks, embeddings = load_embedding_data(json_file)
index = create_faiss_index(embeddings)
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)
embedding_model = SentenceTransformer(embedding_model_name)

# Fonction utilisable directement
def search(query):
    """Perform a search and return the final answer."""
    return generate_response(query, index, chunks, model, tokenizer, embedding_model)

