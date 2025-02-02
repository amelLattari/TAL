import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import matplotlib.pyplot as plt
from datetime import datetime
from decimal import Decimal

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

# Fonction pour récupérer les données financières
def get_stock_data(symbol):
    try:
        connection = connect_db()
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(f"""
                SELECT close_price, date, volume
                FROM stock_prices_yahoo
                WHERE symbol = '{symbol}'
                ORDER BY date DESC
                LIMIT 1;
            """)
            yahoo_data = cursor.fetchone()

            cursor.execute(f"""
                SELECT current_price, high_price, low_price, open_price, timestamp
                FROM stock_prices_finnhub
                WHERE symbol = '{symbol}'
                ORDER BY timestamp DESC
                LIMIT 1;
            """)
            finnhub_data = cursor.fetchone()

            return yahoo_data, finnhub_data
    except Exception as e:
        st.error(f"Erreur lors de la récupération des données : {e}")
    finally:
        if connection:
            connection.close()

# Fonction pour afficher un graphique interactif
def plot_stock_prices(data, symbol):
    dates = [datetime.strptime(row['date'], "%Y-%m-%d") for row in data]
    prices = [row['close_price'] for row in data]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, prices, marker='o', linestyle='-', color='b')
    plt.title(f"Prix de clôture de l'action {symbol}")
    plt.xlabel("Date")
    plt.ylabel("Prix de clôture (USD)")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(plt)

# Fonction pour récupérer les données historiques
def get_historical_stock_data(symbol):
    try:
        connection = connect_db()
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(f"""
                SELECT date, close_price
                FROM stock_prices_yahoo
                WHERE symbol = '{symbol}'
                ORDER BY date ASC;
            """)
            return cursor.fetchall()
    except Exception as e:
        st.error(f"Erreur lors de la récupération des données : {e}")
    finally:
        if connection:
            connection.close()

# Interface Streamlit
st.title("Agent financier interactif")

# Menu de navigation
menu = ["Poser une question", "Calculer des métriques financières", "Afficher un graphique"]
choice = st.sidebar.selectbox("Navigation", menu)

# Option 1 : Poser une question
if choice == "Poser une question":
    question = st.text_input("Posez une question (ex. 'Quel a été le prix de l'action de Apple le 11/12/2023 ?')")
    if st.button("Envoyer"):
        if "prix de l'action" in question.lower():
            symbol = "AAPL"  # Remplacer par une détection réelle
            st.write(f"Prix de l'action {symbol} : 192.23 USD le 11/12/2023")

# Option 2 : Calculer des métriques financières
elif choice == "Calculer des métriques financières":
    symbol = st.text_input("Entrez le symbole de l'entreprise (ex. AAPL pour Apple)")
    if st.button("Calculer"):
        yahoo_data, finnhub_data = get_stock_data(symbol)
        if yahoo_data or finnhub_data:
            close_price = yahoo_data['close_price'] if yahoo_data else finnhub_data['current_price']
            st.write(f"Prix actuel de l'action {symbol}: {close_price} USD")
        else:
            st.write("Données financières introuvables.")

# Option 3 : Afficher un graphique
elif choice == "Afficher un graphique":
    symbol = st.text_input("Entrez le symbole de l'entreprise pour le graphique")
    if st.button("Afficher le graphique"):
        historical_data = get_historical_stock_data(symbol)
        if historical_data:
            plot_stock_prices(historical_data, symbol)
        else:
            st.write("Aucune donnée historique disponible.")
