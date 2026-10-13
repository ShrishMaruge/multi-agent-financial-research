from sqlalchemy import inspect, text

from app.database import engine


NEW_COLUMNS = {
    "confidence": (
        "ALTER TABLE red_flags "
        "ADD COLUMN confidence FLOAT NOT NULL DEFAULT 0.0"
    ),
    "confidence_explanation": (
        "ALTER TABLE red_flags "
        "ADD COLUMN confidence_explanation TEXT NOT NULL DEFAULT ''"
    ),
    "matched_signals": (
        "ALTER TABLE red_flags "
        "ADD COLUMN matched_signals TEXT NOT NULL DEFAULT ''"
    ),
}


def main():
    with engine.begin() as connection:
        existing_columns = {
            column["name"]
            for column in inspect(connection).get_columns("red_flags")
        }

        for column_name, statement in NEW_COLUMNS.items():
            if column_name not in existing_columns:
                connection.execute(text(statement))
                print(f"Added red_flags.{column_name}")
            else:
                print(f"red_flags.{column_name} already exists")

    print("Red Flag database migration completed.")


if __name__ == "__main__":
    main()