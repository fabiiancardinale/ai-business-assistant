import sqlite3


DATABASE = "ai_business.db"


connection = sqlite3.connect(
    DATABASE
)

cursor = connection.cursor()


cursor.execute(
    "PRAGMA table_info(companies)"
)

columns = [
    column[1]
    for column in cursor.fetchall()
]


if "portal_password_hash" not in columns:

    print(
        "Agregando columna portal_password_hash..."
    )

    cursor.execute(
        """
        ALTER TABLE companies
        ADD COLUMN portal_password_hash VARCHAR(255)
        """
    )

    connection.commit()

    print(
        "✓ Columna portal_password_hash agregada correctamente."
    )

else:

    print(
        "✓ La columna portal_password_hash ya existe."
    )


connection.close()

print(
    "✓ Migración del portal de clientes completa."
)