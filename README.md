# 📌 Projet TAL - Finance Chatbot  

## 🚀 Installation et Configuration  

### 1️⃣ Prérequis  
Assurez-vous d'avoir **Python 3** installé.  

### 2️⃣ Installation des dépendances  
```bash
pip install PyPDF2 psycopg2-binary sqlalchemy yfinance
```

### 3️⃣ Configuration PostgreSQL  
L'exécution se fait **en local** (pas sur Google Colab). Assurez-vous que PostgreSQL est installé et en cours d'exécution :  
```bash
sudo systemctl status postgresql
```
Si PostgreSQL n'est pas installé, utilisez :  
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

#### ➤ Configuration des accès  
Modifiez le fichier `pg_hba.conf` :  
```bash
sudo find / -name pg_hba.conf
sudo nano /etc/postgresql/<version>/main/pg_hba.conf
```
Trouvez cette ligne et remplacez `peer` par `md5` :  
```
local   all   all   md5
```
Et remplacez également :  
```
local   all   postgres   peer
```
Par :  
```
local   all   postgres   trust
```
Enregistrez (`Ctrl + O`, puis `Ctrl + X`).

#### ➤ Création des utilisateurs et de la base de données  
Lancez PostgreSQL et exécutez les commandes suivantes :  
```sql
CREATE USER minour WITH PASSWORD 'minour128@';
CREATE DATABASE finance_db;
GRANT ALL PRIVILEGES ON DATABASE finance_db TO minour;
```
Connectez-vous à la base de données depuis un terminal séparé :  
```bash
sudo -u postgres psql
psql -U minour -d finance_db
```
*(Mot de passe : `minour128@`)*  

### 4️⃣ Lancement des tests  
Les tables sont déjà définies dans le code. Exécutez le test avec :  
```bash
python3 test.py
```
Si nécessaire, redémarrez PostgreSQL :  
```bash
sudo systemctl restart postgresql
```

---

## 🎨 Interface Utilisateur  

### 1️⃣ Installation des dépendances  
```bash
pip install streamlit plotly pandas psycopg2 streamlit-chat
```

### 2️⃣ Lancement de l'application  
```bash
streamlit run finance_chatbot.py
```

---

## 📂 Structure du Projet  

```
📁 Projet_TAL_Finance  
│── Pds.zip                 # Archive de données  
│── README.md               # Documentation du projet  
│── embedding.py            # Génération des embeddings  
│── embedding_data.json     # Données d'embeddings  
│── pdf_chunks.json         # Segmentation des PDF  
│── rag.py                  # Modèle RAG (Retrieval-Augmented Generation)  
│── requete.ipynb           # Notebook d'expérimentation et recommandations
│── site.py                 # Interface web principale  
│── site_1.py               # Variante de l'interface  
│── stock_prices_finnhub.json  # Données de prix des actions (Finnhub)  
│── stock_prices_yahoo.json   # Données de prix des actions (Yahoo Finance)  
│── test.py                 # Script de test  
```

---

## 📌 Auteurs  
IKHELEF NOUR 
AMEL LATTARI 
AMINA TADJIN 


