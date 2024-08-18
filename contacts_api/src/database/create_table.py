import psycopg2

user = "postgres"
password = "mysecretpassword"
host = "localhost"
port = "5432"
existing_db = "postgres"
new_db = "contacts_db"

try:
    # # 1. Create the new database
    # connection = psycopg2.connect(
    #     dbname=existing_db,
    #     user=user,
    #     password=password,
    #     host=host,
    #     port=port
    # )
    # connection.autocommit = True
    #
    # with connection.cursor() as cursor:
    #     cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(new_db)))
    # print(f"Database '{new_db}' created successfully!")
    #
    # # 2. Connect to the new database
    # connection.close()  # Close the connection to the existing database
    connection = psycopg2.connect(
        dbname=new_db,
        user=user,
        password=password,
        host=host,
        port=port
    )

    # 3. Create the 'contacts' table
    with connection.cursor() as cursor:
        cursor.execute("""
        CREATE TABLE contacts (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            email VARCHAR(255) UNIQUE,
            phone_number VARCHAR(20),
            birthday DATE,
            additional_info TEXT
        );
        """)
    print("Table 'contacts' created successfully!")

except Exception as e:
    print(f"Error: {e}")

finally:
    if connection:
        connection.close()
