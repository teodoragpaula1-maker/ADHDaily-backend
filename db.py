import os

import psycopg2
from dotenv import load_dotenv

# 1) Load values from the .env file in this folder
load_dotenv()

# 2) Read the DATABASE_URL value from .env
DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """
    Return a new psycopg2 connection using the DATABASE_URL.
    Other files can import this to talk to the database.
    """
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set. Check your .env file.")
    return psycopg2.connect(DATABASE_URL)


def test_connection():
    """
    Simple function to test if we can connect to Supabase Postgres.
    """
    try:
        conn = get_connection()
        print("✅ Connected to Supabase successfully!")
        conn.close()
    except Exception as e:
        print("❌ Connection failed:", e)


if __name__ == "__main__":
    # Run the test when you do: python db.py
    test_connection()
