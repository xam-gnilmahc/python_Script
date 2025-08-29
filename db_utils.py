import mysql.connector

def get_connection(writer=False):
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Alina123@",  # replace with your actual DB password
        database="vox-sneaker"
    )

def execute_query(cnx, sql, fetch=0):
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(sql)

    if fetch == 1:
        result = cursor.fetchone()
    else:
        result = cursor.fetchall()

    cursor.close()
    return {} if fetch == 1 and result is None else (result if result else [])
