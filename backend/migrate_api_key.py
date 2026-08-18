import sqlite3


DATABASE = "ai_business.db"


connection = sqlite3.connect(
    DATABASE
)

cursor = connection.cursor()


# Comprobar si la columna ya existe
cursor.execute(
    "PRAGMA table_info(companies)"
)

columns = [
    column[1]
    for column in cursor.fetchall()
]


if "api_key" not in columns:

    print(
        "Agregando columna api_key..."
    )

    cursor.execute(
        """
        ALTER TABLE companies
        ADD COLUMN api_key VARCHAR(100)
        """
    )

    connection.commit()

    print(
        "✓ Columna api_key agregada correctamente."
    )

else:

    print(
        "✓ La columna api_key ya existe."
    )


connection.close()