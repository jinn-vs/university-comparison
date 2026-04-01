import mysql.connector

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'q200400h$',
    'database': 'university_db'
}

def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn