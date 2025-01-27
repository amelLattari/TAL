import os
import zipfile
import requests
import psycopg2
import pandas as pd
from psycopg2.extras import execute_values
from PyPDF2 import PdfReader
import yfinance as yf

# Configuration de la base de données
DATABASE_CONFIG = {
    "dbname": "finance_db",
    "user": "minour",
    "password": "minour128@",
    "host": "127.0.0.1",
    "port": "5432",
}

# Configuration de l'API Finnhub
FINNHUB_API_KEY = "ctu3eipr01qi2rq6d9k0ctu3eipr01qi2rq6d9kg"

# Chemins pour les PDFs
ZIP_FILE_PATH = "Pds.zip"
EXTRACTION_PATH = "extracted_pdfs"
CHUNK_SIZE = 500  # Taille des chunks en caractères


# Fonction pour supprimer et recréer les tables dans PostgreSQL
def drop_and_create_tables():
    queries = {
        "pdf_chunks": """
            DROP TABLE IF EXISTS pdf_chunks;
            CREATE TABLE pdf_chunks (
                id SERIAL PRIMARY KEY,
                file_name TEXT NOT NULL,
                chunk_number INT NOT NULL,
                chunk_text TEXT NOT NULL
            );
        """,
        "stock_prices_finnhub": """
            DROP TABLE IF EXISTS stock_prices_finnhub;
            CREATE TABLE stock_prices_finnhub (
                symbol TEXT NOT NULL,
                current_price NUMERIC,
                high_price NUMERIC,
                low_price NUMERIC,
                open_price NUMERIC,
                previous_close NUMERIC,
                timestamp DATE NOT NULL,
                PRIMARY KEY (symbol, timestamp)
            );
        """,
        "stock_prices_yahoo": """
            DROP TABLE IF EXISTS stock_prices_yahoo;
            CREATE TABLE stock_prices_yahoo (
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                open_price NUMERIC,
                high_price NUMERIC,
                low_price NUMERIC,
                close_price NUMERIC,
                volume BIGINT,
                PRIMARY KEY (symbol, date)
            );
        """
    }
    try:
        connection = psycopg2.connect(**DATABASE_CONFIG)
        cursor = connection.cursor()
        for table, query in queries.items():
            cursor.execute(query)
        connection.commit()
        print("Tables recréées avec succès.")
    except Exception as e:
        print(f"Erreur lors de la recréation des tables : {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()


# Fonction pour extraire les PDFs du fichier ZIP
def extract_pdfs(zip_path, extraction_path):
    if not os.path.exists(extraction_path):
        os.makedirs(extraction_path)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extraction_path)
    print(f"Fichiers extraits dans {extraction_path}.")
    return [os.path.join(extraction_path, f) for f in os.listdir(extraction_path) if f.endswith('.pdf')]


# Fonction pour lire et diviser le contenu des PDFs en chunks
def pdf_to_chunks(file_path, chunk_size=CHUNK_SIZE):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        # Diviser le texte en chunks
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        return chunks
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier {file_path} : {e}")
        return []


# Fonction pour insérer des données dans PostgreSQL
def insert_into_db(data, table_name):
    try:
        connection = psycopg2.connect(**DATABASE_CONFIG)
        cursor = connection.cursor()
        if table_name == "pdf_chunks":
            insert_query = """
            INSERT INTO pdf_chunks (file_name, chunk_number, chunk_text)
            VALUES %s;
            """
            execute_values(cursor, insert_query, data)
        elif table_name == "stock_prices_finnhub":
            insert_query = """
            INSERT INTO stock_prices_finnhub (symbol, current_price, high_price, low_price, open_price, previous_close, timestamp)
            VALUES %s ON CONFLICT (symbol, timestamp) DO NOTHING;
            """
            execute_values(cursor, insert_query, data)
        elif table_name == "stock_prices_yahoo":
            insert_query = """
            INSERT INTO stock_prices_yahoo (symbol, date, open_price, high_price, low_price, close_price, volume)
            VALUES %s ON CONFLICT (symbol, date) DO NOTHING;
            """
            execute_values(cursor, insert_query, data)
        connection.commit()
        print(f"Données insérées avec succès dans {table_name}.")
    except Exception as e:
        print(f"Erreur lors de l'insertion dans {table_name} : {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()


# Fonction pour récupérer les données des tables et les enregistrer en JSON
def export_table_to_json(table_name, output_file):
    try:
        connection = psycopg2.connect(**DATABASE_CONFIG)
        query = f"SELECT * FROM {table_name};"
        df = pd.read_sql_query(query, connection)
        df.to_json(output_file, orient="records", date_format="iso")
        print(f"Table {table_name} exportée dans {output_file}.")
    except Exception as e:
        print(f"Erreur lors de l'exportation de {table_name} : {e}")
    finally:
        if connection:
            connection.close()


# Fonction principale pour traiter les PDFs
def process_pdfs(zip_file_path):
    pdf_files = extract_pdfs(zip_file_path, EXTRACTION_PATH)
    for pdf_file in pdf_files:
        print(f"Traitement de {pdf_file}...")
        chunks = pdf_to_chunks(pdf_file)
        if chunks:
            data = [(os.path.basename(pdf_file), idx + 1, chunk) for idx, chunk in enumerate(chunks)]
            insert_into_db(data, "pdf_chunks")


# Fonction pour récupérer les prix des actions depuis Finnhub
def fetch_stock_price_finnhub(symbol, date):
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return (symbol, data.get("c"), data.get("h"), data.get("l"), data.get("o"), data.get("pc"), date)
    else:
        print(f"Erreur avec Finnhub pour {symbol}: {response.status_code}")
        return None


# Fonction pour récupérer les données des actions depuis Yahoo Finance
def fetch_stock_data_yahoo(symbol, start_date, end_date):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(start=start_date, end=end_date)
        if not hist.empty:
            row = hist.iloc[-1]
            return (symbol, row.name.date(), row["Open"], row["High"], row["Low"], row["Close"], row["Volume"])
        else:
            print(f"Aucune donnée pour {symbol} entre {start_date} et {end_date}.")
            return None
    except Exception as e:
        print(f"Erreur avec Yahoo Finance pour {symbol}: {e}")
        return None


# Exécution principale
if __name__ == "__main__":
    drop_and_create_tables()

    # Traiter les PDFs
    process_pdfs(ZIP_FILE_PATH)

    # Récupérer et insérer les données boursières
    symbols = ["AAPL", "AMZN", "MSFT"]
    date = "2023-12-12"
    for symbol in symbols:
        data_finnhub = fetch_stock_price_finnhub(symbol, date)
        if data_finnhub:
            insert_into_db([data_finnhub], "stock_prices_finnhub")
        data_yahoo = fetch_stock_data_yahoo(symbol, "2023-12-01", date)
        if data_yahoo:
            insert_into_db([data_yahoo], "stock_prices_yahoo")

    # Exporter les tables en JSON
    export_table_to_json("pdf_chunks", "pdf_chunks.json")
    export_table_to_json("stock_prices_finnhub", "stock_prices_finnhub.json")
    export_table_to_json("stock_prices_yahoo", "stock_prices_yahoo.json")
