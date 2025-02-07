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

def revert_symbol(symbol):
    symbol_map = {
        "AAPL": "Apple",
        "AMZN": "Amazon",
        "MSFT": "Microsoft"
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

# Fonction pour calculer le RSI
def calculate_rsi(prices, period=14):
    if len(prices) < period:
        return Decimal('55.0')  # Valeur neutre si nous n'avons pas assez de données

    # Calcul des variations de prix
    deltas = np.diff(prices)
    gains = np.maximum(deltas, 0)
    losses = -np.minimum(deltas, 0)

    # Moyennes des gains et pertes
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    # Éviter la division par zéro
    if avg_loss == 0:
        return Decimal('100.0')

    # Calcul du RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return Decimal(rsi)

# Fonction principale pour calculer les métriques
def calculate_metrics(yahoo_data, finnhub_data):
    if not yahoo_data and not finnhub_data:
        st.warning("Données insuffisantes pour effectuer les calculs.")
        return None

    close_price = Decimal(yahoo_data[0]['close_price']) if yahoo_data else Decimal(finnhub_data[0]['current_price'])
    volume = yahoo_data[0]['volume'] if yahoo_data else 0

    # Exemple de récupération de données fondamentales
    net_income = Decimal('95000000000')
    shares_outstanding = Decimal('15700000000')

    # Calcul des indicateurs financiers
    eps = net_income / shares_outstanding
    pe_ratio = close_price / eps
    market_cap = close_price * shares_outstanding

    # Préparation des données pour le calcul du RSI
    close_prices = [Decimal(row['close_price']) for row in yahoo_data]
    rsi = calculate_rsi(close_prices)

    return {
        "EPS": eps,
        "P/E Ratio": pe_ratio,
        "Market Capitalization": market_cap,
        "Close Price": close_price,
        "Volume": volume,
        "RSI": rsi,
    }

# Fonction pour afficher un graphique des prix de clôture
def plot_stock_prices(data, symbol, sym):
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

# Fonction pour obtenir une recommandation basée sur les indicateurs
def get_recommendation(symbol, metrics):
    try:
        # Charger le modèle et le scaler
        with open("recommendation_model.pkl", "rb") as f:
            model = pickle.load(f)
        with open("scaler.pkl", "rb") as f:
            scaler = pickle.load(f)

        # Préparer les données pour le modèle
        data = pd.DataFrame([{
            "rsi": float(metrics["RSI"]),
            "macd": 0.0,  # Remplacez par un calcul réel du MACD si disponible
            "eps": float(metrics["EPS"]),
            "pe_ratio": float(metrics["P/E Ratio"])
        }])

        # Appliquer le scaler et prédire
        X = scaler.transform(data)
        prediction = model.predict(X)[0]

        # Décision basée sur la prédiction
        decision = {
            1: "Acheter (Buy)",
            0: "Vendre (Sell)",
            -1: "Conserver (Hold)"
        }.get(prediction, "Aucune recommandation disponible")

        # Explication détaillée
        explanation = (
            f"🔍 Analyse des indicateurs pour {symbol} :\n"
            f"📈 **RSI** : {metrics['RSI']:.2f} (Indice de force relative)\n"
            f"📊 **MACD** : 0.00 (Tendance court-terme)\n"  # Remplacez par un calcul réel du MACD
            f"💵 **EPS** : {metrics['EPS']:.2f} (Bénéfice par action)\n"
            f"📉 **P/E Ratio** : {metrics['P/E Ratio']:.2f} (Valorisation de l'action)\n"
        )

        if metrics['RSI'] < 30:
            explanation += "✅ Le RSI est faible, l'action est sous-évaluée, ce qui peut être une opportunité d'achat.\n"
        elif metrics['RSI'] > 70:
            explanation += "⚠️ Le RSI est élevé, l'action pourrait être surévaluée.\n"

        return decision, explanation
    except Exception as e:
        st.error(f"Erreur lors de la génération de la recommandation : {e}")
        return "Erreur", f"Une erreur s'est produite : {e}"

# Fonction pour afficher des recommandations
def display_recommendations(symbol, metrics):
    st.subheader("Recommandations")
    decision, explanation = get_recommendation(symbol, metrics)
    st.write(f"**Recommandation :** {decision}")
    st.write("📢 **Justification détaillée :**")
    st.write(explanation)

# Fonction pour le chatbot interactif
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

# Interface Streamlit
def main():
    st.set_page_config(page_title="Chatbot Financier", page_icon="📈", layout="wide")

    # Menu de navigation
    st.sidebar.title("Navigation")
    option = st.sidebar.radio("Choisissez une option", ["Accueil", "Recherche d'actions", "Chatbot", "Aide"])

    if option == "Accueil":
        st.header("Bienvenue sur le Chatbot Financier")
        st.write("Explorez les données financières et obtenez des recommandations.")

    elif option == "Recherche d'actions":
        st.header("Recherche d'actions")
        def get_available_symbols():
            connection = connect_db()
            with connection.cursor() as cursor:
                cursor.execute("SELECT DISTINCT symbol FROM stock_prices_yahoo")
                return [row[0] for row in cursor.fetchall()]

        symbols = get_available_symbols()
        company_names = [revert_symbol(symbol) for symbol in symbols]
        sym = st.selectbox("Choisissez une entreprise :", company_names)
        symbol = convert_symbol(sym)
        if symbol:
            yahoo_data, finnhub_data = get_stock_data(symbol)
            if yahoo_data:
                st.subheader(f"Données pour {sym}")
                plot_stock_prices(yahoo_data, symbol, sym)

                metrics = calculate_metrics(yahoo_data, finnhub_data)
                if metrics:
                    st.subheader(f"Métriques financières pour {sym}")

                    # Affichage des métriques avec infobulles
                    st.write(f"Prix actuel de l'action : {metrics['Close Price']} USD")
                    with st.expander("ℹ️ EPS"):
                        st.write("**EPS (Earnings Per Share)** : Le bénéfice par action est un indicateur de la rentabilité d'une entreprise.")
                    st.write(f"EPS : {metrics['EPS']:.2f} USD")

                    with st.expander("ℹ️ P/E Ratio"):
                        st.write("**P/E Ratio (Price-to-Earnings Ratio)** : Le ratio cours/bénéfice mesure la valorisation d'une action.")
                    st.write(f"Ratio P/E : {metrics['P/E Ratio']:.2f}")

                    st.write(f"Capitalisation boursière : {metrics['Market Capitalization']:.2f} USD")
                    st.write(f"Volume échangé : {metrics['Volume']} actions")

                    with st.expander("ℹ️ RSI"):
                        st.write("**RSI (Relative Strength Index)** : Un indicateur technique qui mesure la vitesse et le changement des mouvements de prix.")
                    st.write(f"RSI : {metrics['RSI']}")

                    # Affichage des recommandations
                    display_recommendations(symbol, metrics)

    elif option == "Chatbot":
        st.header("Chatbot Financier")
        if 'responses' not in st.session_state:
            st.session_state['responses'] = []
        if 'requests' not in st.session_state:
            st.session_state['requests'] = []

        user_input = st.text_input("Posez une question :")
        if user_input:
            response = chatbot_response(user_input)
            st.session_state.requests.append(user_input)
            st.session_state.responses.append(response)

        for i in range(len(st.session_state.responses)):
            message(st.session_state.requests[i], is_user=True, key=f"user_{i}")
            message(st.session_state.responses[i], key=f"bot_{i}")

    elif option == "Aide":
        st.header("Aide")
        st.write("### Comment utiliser l'application :")
        st.write("1. **Recherche d'actions** : Entrez le nom de l'entreprise pour obtenir des données financières.")
        st.write("2. **Chatbot** : Posez des questions en langage naturel pour obtenir des informations spécifiques. Exemple (Quel a été le prix de l'action d'Apple le 11/12/2023 ?)")
        st.write("3. **Recommandations** : Consultez les recommandations basées sur les indicateurs financiers.")

# Exécution de l'application Streamlit
if __name__ == "__main__":
    main()
