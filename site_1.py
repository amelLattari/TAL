import psycopg2
from psycopg2.extras import RealDictCursor
import re
from decimal import Decimal
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from streamlit_chat import message
import pickle
import numpy as np

# Importation des fonctions RAG
from rag import search_documents_from_zip

# Configuration de la base de données
DATABASE_CONFIG = {
    "dbname": "finance_db",
    "user": "minour",
    "password": "minour128@",
    "host": "127.0.0.1",
    "port": "5432",
}

# Fonction pour se connecter à la base de données
def connect_db():
    return psycopg2.connect(**DATABASE_CONFIG)

# Fonction pour récupérer les données financières de la base
@st.cache_data
def get_stock_data(symbol):
    try:
        connection = connect_db()
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(f"""
                SELECT close_price, date, volume
                FROM stock_prices_yahoo
                WHERE symbol = '{symbol}'
                ORDER BY date DESC;
            """)
            yahoo_data = cursor.fetchall()

            cursor.execute(f"""
                SELECT current_price, high_price, low_price, open_price, timestamp
                FROM stock_prices_finnhub
                WHERE symbol = '{symbol}'
                ORDER BY timestamp DESC;
            """)
            finnhub_data = cursor.fetchall()

            return yahoo_data, finnhub_data
    except Exception as e:
        st.error(f"Erreur lors de la récupération des données : {e}")
    finally:
        if connection:
            connection.close()

# Fonction pour exécuter une requête utilisateur sur les actions
def chatbot_response(user_input):
    query_type, details = parse_query(user_input)
    if query_type == "stock_price":
        symbol, date = details
        sql_query = generate_sql(query_type, details)
        results = execute_query(sql_query)
        if results:
            return f"Le prix de clôture de {symbol} le {date} était {results[0]['close_price']} USD."
        else:
            return f"Aucune donnée trouvée pour {symbol} le {date}."
    else:
        return "Je ne comprends pas votre question. Pouvez-vous reformuler ?"

# Autres fonctions pour les graphiques et calculs financiers
# (Gardées telles quelles...)

def main():
    st.set_page_config(page_title="Chatbot Financier avec RAG", page_icon="📈", layout="wide")

    st.sidebar.title("Navigation")
    option = st.sidebar.radio("Choisissez une option", ["Accueil", "Recherche d'actions", "Chatbot (SQL)", "RAG", "Aide"])

    if option == "Accueil":
        st.header("Bienvenue sur le Chatbot Financier")
        st.write("Explorez les données financières et obtenez des recommandations.")

    elif option == "Recherche d'actions":
        st.header("Recherche d'actions")
        symbols = ["AAPL", "AMZN", "MSFT"]  # Exemple
        sym = st.selectbox("Choisissez une entreprise :", symbols)
        if sym:
            yahoo_data, finnhub_data = get_stock_data(sym)
            if yahoo_data:
                st.subheader(f"Données pour {sym}")
                plot_stock_prices(yahoo_data, sym, sym)

                metrics = calculate_metrics(yahoo_data, finnhub_data)
                if metrics:
                    st.write(f"Prix actuel : {metrics['Close Price']} USD")
                    st.write(f"EPS : {metrics['EPS']:.2f} USD")
                    st.write(f"Ratio P/E : {metrics['P/E Ratio']:.2f}")
                    st.write(f"Capitalisation boursière : {metrics['Market Capitalization']:.2f} USD")
                    st.write(f"RSI : {metrics['RSI']}")

    elif option == "Chatbot (SQL)":
        st.header("Chatbot Financier (basé sur SQL)")
        if 'responses' not in st.session_state:
            st.session_state['responses'] = []
        if 'requests' not in st.session_state:
            st.session_state['requests'] = []

        user_input = st.text_input("Posez une question (ex : prix de l'action) :")
        if user_input:
            response = chatbot_response(user_input)
            st.session_state.requests.append(user_input)
            st.session_state.responses.append(response)

        for i in range(len(st.session_state.responses)):
            message(st.session_state.requests[i], is_user=True, key=f"user_sql_{i}")
            message(st.session_state.responses[i], key=f"bot_sql_{i}")

    elif option == "RAG":
        st.header("Chatbot Financier avec RAG")

        # Téléchargement du fichier ZIP
        uploaded_file = st.file_uploader("Téléchargez un fichier ZIP contenant des documents PDF", type=["zip"])

        if uploaded_file:
            query = st.text_input("Posez une question sur les documents :")
            if query:
                response = search_documents_from_zip(uploaded_file, query)
                st.write(f"📝 **Réponse :** {response}")
        else:
            st.warning("Veuillez télécharger un fichier ZIP contenant des documents.")

    elif option == "Aide":
        st.header("Aide")
        st.write("### Utilisation de l'application :")
        st.write("1. **Recherche d'actions** : Entrez le nom de l'entreprise pour obtenir des données.")
        st.write("2. **Chatbot (SQL)** : Posez des questions sur les données stockées en base.")
        st.write("3. **RAG** : Posez des questions sur les documents téléchargés.")
        st.write("4. **Recommandations** : Consultez les indicateurs financiers.")

# Lancer l'application
if __name__ == "__main__":
    main()