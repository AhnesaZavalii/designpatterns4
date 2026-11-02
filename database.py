import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path(__file__).with_name("weather_history.db")


class WeatherHistory:

    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = str(db_path)
        self._create_table()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS forecast_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    retrieved_at TEXT NOT NULL,
                    forecast_time TEXT NOT NULL,
                    temperature_c REAL NOT NULL,
                    precipitation_probability REAL,
                    source TEXT NOT NULL
                )
                """
            )

    def save(self, forecast):
        try:
            with self._connect() as connection:
                connection.executemany(
                    """
                    INSERT INTO forecast_history (
                        city, latitude, longitude, retrieved_at,
                        forecast_time, temperature_c,
                        precipitation_probability, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            forecast.city,
                            forecast.latitude,
                            forecast.longitude,
                            forecast.retrieved_at,
                            hour.time,
                            hour.temperature_c,
                            hour.precipitation_probability,
                            forecast.source,
                        )
                        for hour in forecast.hours
                    ],
                )
        except sqlite3.Error as error:
            raise RuntimeError(f"Помилка запису до SQLite: {error}") from error

    def get_recent(self, city=None, limit=20):
        try:
            with self._connect() as connection:
                connection.row_factory = sqlite3.Row
                if city:
                    rows = connection.execute(
                        """
                        SELECT * FROM forecast_history
                        WHERE city = ? COLLATE NOCASE
                        ORDER BY id DESC LIMIT ?
                        """,
                        (city, limit),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        """
                        SELECT * FROM forecast_history
                        ORDER BY id DESC LIMIT ?
                        """,
                        (limit,),
                    ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as error:
            raise RuntimeError(f"Помилка читання SQLite: {error}") from error
