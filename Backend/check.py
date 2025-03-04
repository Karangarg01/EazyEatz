from db_helper import cnx

cursor = cnx.cursor()
cursor.execute("SHOW TABLES;")
tables = cursor.fetchall()

print("Available tables in the database:", tables)

cursor.close()
cnx.close()