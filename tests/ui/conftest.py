import sqlite3

import pytest


@pytest.fixture(autouse=True)
def patch_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE stats (
            id INTEGER PRIMARY KEY,
            municipality TEXT NOT NULL,
            area_type TEXT NOT NULL,
            area_slug TEXT NOT NULL,
            area_name TEXT,
            url TEXT NOT NULL,
            category TEXT,
            topic TEXT NOT NULL,
            value TEXT,
            unit TEXT,
            year TEXT,
            scraped_at TEXT NOT NULL,
            UNIQUE (area_slug, topic)
        );
        CREATE TABLE area_hierarchy (
            municipality TEXT,
            wijk_slug TEXT,
            wijk_name TEXT,
            buurt_slug TEXT,
            buurt_name TEXT,
            PRIMARY KEY(municipality, buurt_slug)
        );
        INSERT INTO stats VALUES
            (1,'amsterdam','wijk','oud-west-amsterdam','Oud-West',
             'https://allecijfers.nl/wijk/oud-west-amsterdam/',
             'Bevolking','Inwoners','25000','Aantal','2023','2024-01-01'),
            (2,'amsterdam','wijk','oud-west-amsterdam','Oud-West',
             'https://allecijfers.nl/wijk/oud-west-amsterdam/',
             'Inkomen','Gemiddeld inkomen per inwoner','35000','€','2022','2024-01-01'),
            (3,'amsterdam','wijk','oud-west-amsterdam','Oud-West',
             'https://allecijfers.nl/wijk/oud-west-amsterdam/',
             'Woningen','% Huurwoningen','65','%','2023','2024-01-01'),
            (4,'amsterdam','wijk','oud-west-amsterdam','Oud-West',
             'https://allecijfers.nl/wijk/oud-west-amsterdam/',
             'Misdrijven','Misdrijven','500','Aantal','2023','2024-01-01'),
            (5,'amsterdam','buurt','de-pijp-amsterdam','De Pijp',
             'https://allecijfers.nl/buurt/de-pijp-amsterdam/',
             'Bevolking','Inwoners','15000','Aantal','2023','2024-01-01'),
            (6,'haarlem','buurt','centrum-haarlem','Centrum',
             'https://allecijfers.nl/buurt/centrum-haarlem/',
             'Bevolking','Inwoners','8000','Aantal','2023','2024-01-01'),
            (7,'amsterdam','wijk','oud-west-amsterdam','Oud-West',
             'https://allecijfers.nl/wijk/oud-west-amsterdam/',
             'Migratie','% Herkomst buiten Europa','32%','Percentage','2023','2024-01-01');
        INSERT INTO area_hierarchy VALUES
            ('amsterdam','oud-west-amsterdam','Oud-West','de-pijp-amsterdam','De Pijp');
    """)
    conn.commit()
    conn.close()
    monkeypatch.setattr("ui.db.DB_PATH", db_path)
    monkeypatch.setattr("ui.db._translations", None)


@pytest.fixture
def client():
    from ui.main import app
    from fastapi.testclient import TestClient
    return TestClient(app, follow_redirects=True)
