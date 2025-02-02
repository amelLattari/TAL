import psycopg2
from psycopg2.extras import RealDictCursor
import re
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

# Fonction pour récupérer les données financières de la base
def get_stock_data(symbol):
    try:
        connection = connect_db()
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            # Récupération des prix à partir de stock_prices_yahoo
            cursor.execute(f"""
                SELECT close_price, date, volume
                FROM stock_prices_yahoo
                WHERE symbol = '{symbol}'
                ORDER BY date DESC
                LIMIT 1;
            """)
            yahoo_data = cursor.fetchone()

            # Récupération des prix à partir de stock_prices_finnhub
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
        print(f"Erreur lors de la récupération des données : {e}")
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
        print(f"Erreur lors de l'exécution de la requête : {e}")
    finally:
        if connection:
            connection.close()

# Fonction pour calculer les métriques financières
def calculate_metrics(yahoo_data, finnhub_data):
    if not yahoo_data and not finnhub_data:
        print("Données insuffisantes pour effectuer les calculs.")
        return None

    close_price = Decimal(yahoo_data['close_price']) if yahoo_data else Decimal(finnhub_data['current_price'])
    volume = yahoo_data['volume'] if yahoo_data else 0

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

# Fonction pour traiter la requête utilisateur
def handle_user_query(user_query):
    query_type, details = parse_query(user_query)
    if not query_type:
        print("Impossible d'interpréter la requête.")
        return

    sql_query = generate_sql(query_type, details)
    if not sql_query:
        print("Impossible de générer une requête SQL.")
        return

    print("Requête SQL générée :")
    print(sql_query)

    results = execute_query(sql_query)
    if results:
        for row in results:
            print(f"Prix de clôture : {row['close_price']} le {row['date']}")
    else:
        print("Aucune donnée trouvée pour la requête.")

# Fonction principale
def main():
    user_query = input("Entrez votre requête ou tapez une entreprise (ex. 'prix de l'action de Apple le 11/12/2023') : ")
    handle_user_query(user_query)

    symbol = input("\nEntrez le symbole de l'entreprise (ex. AAPL pour Apple) : ").upper()
    yahoo_data, finnhub_data = get_stock_data(symbol)
    metrics = calculate_metrics(yahoo_data, finnhub_data)

    if metrics:
        print("\nMétriques financières pour", symbol)
        print(f"Prix actuel de l'action : {metrics['Close Price']} USD")
        print(f"EPS : {metrics['EPS']:.2f} USD")
        print(f"Ratio P/E : {metrics['P/E Ratio']:.2f}")
        print(f"Capitalisation boursière : {metrics['Market Capitalization']:.2f} USD")
        print(f"Volume échangé : {metrics['Volume']} actions")

# Exécution du script
if __name__ == "__main__":
    main()
