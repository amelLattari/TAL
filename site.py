import psycopg2
from psycopg2.extras import RealDictCursor
import re
from decimal import Decimal
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

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

# Fonction pour analyser la requête utilisateur
def parse_query(user_query):
    pattern = r"prix de l'action\s*(?:d[e’']\s*)?(\w+)\s+le\s+(\d{2}/\d{2}/\d{4})"
    match = re.search(pattern, user_query, re.IGNORECASE)
    if match:
        return "stock_price", match.groups()
    return None, None

# Fonction pour convertir les symboles au format attendu par la base
def convert_symbol(symbol):
    symbol_map = {
        "APPLE": "AAPL",
        "AMAZON": "AMZN",
        "MICROSOFT": "MSFT"
    }
    return symbol_map.get(symbol.upper(), symbol.upper())

# Fonction pour générer une requête SQL
def generate_sql(query_type, details):
    if query_type == "stock_price":
        symbol, date = details
        date_sql = "-".join(reversed(date.split('/')))
        symbol_sql = convert_symbol(symbol)
        return f"""
            SELECT close_price, date
            FROM stock_prices_yahoo
            WHERE symbol = '{symbol_sql}' AND date = '{date_sql}';
        """
    return None

# Fonction pour exécuter une requête SQL
def execute_query(sql_query):
    try:
        connection = connect_db()
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql_query)
            return cursor.fetchall()
    except Exception as e:
        st.error(f"Erreur lors de l'exécution de la requête : {e}")
    finally:
        if connection:
            connection.close()

# Fonction pour calculer les métriques financières
def calculate_metrics(yahoo_data, finnhub_data):
    if not yahoo_data and not finnhub_data:
        st.warning("Données insuffisantes pour effectuer les calculs.")
        return None

    close_price = Decimal(yahoo_data[0]['close_price']) if yahoo_data else Decimal(finnhub_data[0]['current_price'])
    volume = yahoo_data[0]['volume'] if yahoo_data else 0

    net_income = Decimal('95000000000')
    shares_outstanding = Decimal('15700000000')
    eps = net_income / shares_outstanding
    pe_ratio = close_price / eps
    market_cap = close_price * shares_outstanding

    return {
        "EPS": eps,
        "P/E Ratio": pe_ratio,
        "Market Capitalization": market_cap,
        "Close Price": close_price,
        "Volume": volume,
    }

# Fonction pour afficher un graphique des prix de clôture
def plot_stock_prices(data, symbol,sym):
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date')

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['close_price'], mode='lines', name='Prix de clôture'))
    fig.update_layout(
    title=f"Historique des prix de clôture pour {sym}",
    xaxis_title="Date",
    yaxis_title="Prix de clôture (USD)",
    xaxis=dict(tickformat="%Y-%m-%d"),
    template="plotly_dark"
    )
    st.plotly_chart(fig)

# Fonction pour afficher des recommandations
def display_recommendations(metrics):
    if metrics['P/E Ratio'] < 15:
        st.success("Recommandation : Acheter (Ratio P/E bas)")
    elif metrics['P/E Ratio'] > 25:
        st.warning("Recommandation : Vendre (Ratio P/E élevé)")
    else:
        st.info("Recommandation : Maintenir (Ratio P/E modéré)")

# Interface Streamlit
def main():
    st.title("Chatbot d'Informations Financières")

    user_query = st.text_input("Entrez votre question (ex. 'Quel a été le prix de l'action d'Apple le 13/12/2023 ?') :")
    if user_query:
        handle_user_query(user_query)

    sym = st.text_input("Entrez le nom de l'entreprise :")
    symbol = convert_symbol(sym)
    if symbol:
        yahoo_data, finnhub_data = get_stock_data(symbol)
        if yahoo_data:
            st.subheader(f"Données pour {sym}")
            plot_stock_prices(yahoo_data, symbol, sym)

            metrics = calculate_metrics(yahoo_data, finnhub_data)
            if metrics:
                st.subheader(f"Métriques financières pour {sym}")
                st.write(f"Prix actuel de l'action : {metrics['Close Price']} USD")
                st.write(f"EPS : {metrics['EPS']:.2f} USD")
                st.write(f"Ratio P/E : {metrics['P/E Ratio']:.2f}")
                st.write(f"Capitalisation boursière : {metrics['Market Capitalization']:.2f} USD")
                st.write(f"Volume échangé : {metrics['Volume']} actions")

                # Affichage des recommandations
                st.subheader("Recommandations")
                display_recommendations(metrics)

# Fonction pour traiter la requête utilisateur
def handle_user_query(user_query):
    query_type, details = parse_query(user_query)
    if not query_type:
        st.error("Impossible d'interpréter la requête.")
        return

    sql_query = generate_sql(query_type, details)
    if not sql_query:
        st.error("Impossible de générer une requête SQL.")
        return

    st.text("Requête SQL générée :")
    st.code(sql_query)

    results = execute_query(sql_query)
    if results:
        for row in results:
            st.success(f"Prix de clôture : {row['close_price']} le {row['date']}")
    else:
        st.info("Aucune donnée trouvée pour la requête.")

# Exécution de l'application Streamlit
if __name__ == "__main__":
    main()
