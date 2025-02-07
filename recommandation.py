import psycopg2
import pandas as pd
import numpy as np
import pickle
import yfinance as yf
from decimal import Decimal
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# 📌 Configuration de la base de données PostgreSQL
DATABASE_CONFIG = {
    "dbname": "finance_db",
    "user": "minour",
    "password": "minour128@",
    "host": "127.0.0.1",
    "port": "5432",
}

# 📌 Connexion à la base
def connect_db():
    return psycopg2.connect(**DATABASE_CONFIG)

# 📌 Vérification et création de la table `stock_analysis_data`
def create_table():
    query = """
    CREATE TABLE IF NOT EXISTS stock_analysis_data (
        symbol TEXT PRIMARY KEY,
        rsi NUMERIC,
        macd NUMERIC,
        eps NUMERIC,
        pe_ratio NUMERIC,
        recommendation INTEGER DEFAULT 0
    );
    """
    connection = connect_db()
    with connection.cursor() as cursor:
        cursor.execute(query)
        connection.commit()
    connection.close()

# 📌 Récupération des prix d'une action
def get_stock_data(symbol):
    try:
        connection = connect_db()
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT close_price, date
                FROM stock_prices_yahoo
                WHERE symbol = '{symbol}'
                ORDER BY date DESC
                LIMIT 14;  -- Nécessaire pour RSI
            """)
            yahoo_data = cursor.fetchall()
        return yahoo_data
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération des données pour {symbol} : {e}")
        return None
    finally:
        connection.close()

# 📌 Calcul du RSI
def calculate_rsi(prices, period=14):
    if len(prices) < period:
        return 50  # Valeur neutre

    deltas = np.diff(prices)
    gains = np.maximum(deltas, 0)
    losses = -np.minimum(deltas, 0)

    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)

    if avg_loss == 0:
        return 100  # Si aucune perte, RSI = 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# 📌 Calcul du MACD
def calculate_macd(prices):
    short_ema = pd.Series(prices).ewm(span=12, adjust=False).mean()
    long_ema = pd.Series(prices).ewm(span=26, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd.iloc[-1] - signal.iloc[-1]

# 📌 Calcul des indicateurs fondamentaux
def calculate_metrics(yahoo_data):
    if not yahoo_data:
        return None
    close_prices = [row[0] for row in yahoo_data if row[0] is not None]
    if not close_prices:
        return None
    close_price = Decimal(close_prices[-1])
    
    # Exemple de données fixes
    net_income = Decimal('95000000000')  # Exemple : à récupérer dynamiquement
    shares_outstanding = Decimal('15700000000')
    if shares_outstanding == 0:
        return None
    eps = net_income / shares_outstanding
    pe_ratio = close_price / eps if eps > 0 else None

    rsi = calculate_rsi(close_prices)
    macd = calculate_macd(close_prices)

    return {
        "RSI": rsi,
        "MACD": macd,
        "EPS": eps,
        "P/E Ratio": pe_ratio
    }

# 📌 Insertion des données dans PostgreSQL
def insert_into_stock_analysis(symbol, metrics):
    if not metrics:
        return
    try:
        connection = connect_db()
        with connection.cursor() as cursor:
            query = """
                INSERT INTO stock_analysis_data (symbol, rsi, macd, eps, pe_ratio, recommendation)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol) DO UPDATE
                SET rsi = EXCLUDED.rsi,
                    macd = EXCLUDED.macd,
                    eps = EXCLUDED.eps,
                    pe_ratio = EXCLUDED.pe_ratio,
                    recommendation = EXCLUDED.recommendation;
            """
            cursor.execute(query, (symbol, metrics["RSI"], metrics["MACD"], metrics["EPS"], metrics["P/E Ratio"], 0))
            connection.commit()
            print(f"✅ Données insérées pour {symbol}")
    finally:
        connection.close()

# 📌 Entraînement du modèle
def train_model():
    connection = connect_db()
    query = "SELECT rsi, macd, eps, pe_ratio, recommendation FROM stock_analysis_data"
    df = pd.read_sql_query(query, connection)
    connection.close()
    
    if df.empty:
        print("⚠️ Pas assez de données pour entraîner le modèle.")
        return

    # Suppression des valeurs manquantes
    df = df.dropna()

    if df.empty:
        print("⚠️ Toutes les lignes avaient des valeurs manquantes. Impossible d'entraîner le modèle.")
        return

    X = df.drop(columns=["recommendation"])
    y = df["recommendation"]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    with open("recommendation_model.pkl", "wb") as f:
        pickle.dump(model, f)
    with open("scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)

    print("✅ Modèle entraîné et sauvegardé.")


# 📌 Justification des recommandations
def get_recommendation(symbol):
    connection = connect_db()
    query = f"SELECT rsi, macd, eps, pe_ratio FROM stock_analysis_data WHERE symbol = '{symbol}';"
    df = pd.read_sql_query(query, connection)
    connection.close()

    if df.empty:
        return "Données insuffisantes", "Aucune donnée trouvée."

    # Vérifier si certaines valeurs sont None
    for col in ["rsi", "macd", "eps", "pe_ratio"]:
        if pd.isna(df[col][0]):
            return "Données insuffisantes", f"La valeur de {col} est manquante."

    with open("recommendation_model.pkl", "rb") as f:
        model = pickle.load(f)
    with open("scaler.pkl", "rb") as f:
        scaler = pickle.load(f)

    X = scaler.transform(df)
    prediction = model.predict(X)[0]

    decision = {1: "Acheter (Buy)", 0: "Vendre (Sell)", -1: "Conserver (Hold)"}[prediction]
    return decision, f"RSI: {df['rsi'][0]}, MACD: {df['macd'][0]}, EPS: {df['eps'][0]}, P/E Ratio: {df['pe_ratio'][0]}"

# 📌 Exécution principale
if __name__ == "__main__":
    create_table()
    symbols = ["AAPL", "AMZN", "MSFT"]
    for symbol in symbols:
        yahoo_data = get_stock_data(symbol)
        metrics = calculate_metrics(yahoo_data)
        insert_into_stock_analysis(symbol, metrics)
    
    train_model()
    
    symbol = input("Entrez le symbole de l'action (ex: AAPL, MSFT) : ").upper()
    decision, explanation = get_recommendation(symbol)
    print(f"\n🔎 Recommandation pour {symbol} : {decision}")
    print(f"📢 Justification : {explanation}")
