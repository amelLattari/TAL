# TAL
# Bibliotheque Python3

pip install PyPDF2 psycopg2-binary sqlalchemy yfinance
l'execution en local pas sur collab sur un terminal local (check lancement postgres sudo systemctl status postgresql)
sudo apt update

sudo apt install postgresql postgresql-contrib
sudo find / -name pg_hba.conf
sudo nano /etc/postgresql/<version>/main/pg_hba.conf
Locate the line that looks like this (usually near the top):


local   all   all   peer

Change peer to md5 so it looks like this:


local   all   all   md5

Localise les lignes suivantes :

local   all             postgres                                peer
Remplace peer par trust pour permettre à l'utilisateur postgres de se connecter sans mot de passe :


local   all             postgres                                trust

Save the file and exit (Ctrl + O, then Ctrl + X).
CREATE USER minour WITH PASSWORD 'minour128@';
CREATE ROLE
CREATE DATABASE finance_db;
GRANT ALL PRIVILEGES ON DATABASE finance_db TO minour;

sudo -u postgres psql
sur un autre terminal: psql -U minour -d finance_db

minour128@ pour le mp

apres les tables sont dans le code

python3 test.py

sudo systemctl restart postgresql

# interface utilisateur
pip install streamlit plotly pandas psycopg2 streamlit-chat
streamlit run finance_chatbot.py



