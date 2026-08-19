import sqlite3


DATABASE = "ai_business.db"


connection = sqlite3.connect(
    DATABASE
)

cursor = connection.cursor()


# Comprobar qué columnas ya existen
cursor.execute(
    "PRAGMA table_info(companies)"
)

columns = [
    column[1]
    for column in cursor.fetchall()
]


if "primary_color" not in columns:

    print(
        "Agregando columna primary_color..."
    )

    cursor.execute(
        """
        ALTER TABLE companies
        ADD COLUMN primary_color VARCHAR(20) DEFAULT '#111827'
        """
    )

    connection.commit()

    print(
        "✓ Columna primary_color agregada correctamente."
    )

else:

    print(
        "✓ La columna primary_color ya existe."
    )


if "icon" not in columns:

    print(
        "Agregando columna icon..."
    )

    cursor.execute(
        """
        ALTER TABLE companies
        ADD COLUMN icon VARCHAR(255) DEFAULT '💬'
        """
    )

    connection.commit()

    print(
        "✓ Columna icon agregada correctamente."
    )

else:

    print(
        "✓ La columna icon ya existe."
    )


if "icon_has_background" not in columns:

    print(
        "Agregando columna icon_has_background..."
    )

    cursor.execute(
        """
        ALTER TABLE companies
        ADD COLUMN icon_has_background BOOLEAN DEFAULT 1
        """
    )

    connection.commit()

    print(
        "✓ Columna icon_has_background agregada correctamente."
    )

else:

    print(
        "✓ La columna icon_has_background ya existe."
    )


# Rellenar valores por defecto en empresas que ya existían
# (ALTER TABLE con DEFAULT en SQLite solo aplica a filas nuevas,
# no completa automáticamente las filas ya existentes).

cursor.execute(
    """
    UPDATE companies
    SET primary_color = '#111827'
    WHERE primary_color IS NULL
    """
)

cursor.execute(
    """
    UPDATE companies
    SET icon = '💬'
    WHERE icon IS NULL
    """
)

cursor.execute(
    """
    UPDATE companies
    SET icon_has_background = 1
    WHERE icon_has_background IS NULL
    """
)

connection.commit()


connection.close()

print(
    "✓ Migración de apariencia completa."
)