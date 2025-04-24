from sqlalchemy import create_engine
import os

db_url = "postgresql://postgres.unelbsbpsyqmnjfoukch:5YFxognEMKItzu@aws-0-us-east-2.pooler.supabase.com:6543/postgres"

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        print("✅ Connected")
except Exception as e:
    print("❌ Failed:", e)
