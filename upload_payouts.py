import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import sys

# Load the .env file
load_dotenv()
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

if not SUPABASE_DB_URL:
    print("❌ Error: SUPABASE_DB_URL not found in environment variables.")
    sys.exit(1)

# --- ARGUMENTS ---
if len(sys.argv) != 3:
    print("❌ Usage: python upload_payouts.py <csv_filename> <month_tag>")
    sys.exit(1)

csv_file = sys.argv[1]
month_tag = sys.argv[2]

if not os.path.exists(csv_file):
    print(f"❌ File not found: {csv_file}")
    sys.exit(1)

# --- LOAD AND CLEAN DATA ---
df = pd.read_csv(csv_file)

# Normalize headers (remove spaces, lowercase)
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

# Explicitly rename to match DB schema
df = df.rename(columns={
    'email_id': 'email',
    'phone_number': 'phone',
    'langauge': 'language',
    'tds_applicability': 'tds_applicable'
})

if 'tds_applicable' in df.columns:
    df['tds_applicable'] = df['tds_applicable'].astype(str).str.lower().map({'yes': True, 'no': False})
df['month'] = month_tag

# --- DATABASE UPLOAD ---
try:
    engine = create_engine(SUPABASE_DB_URL)
    df.to_sql('payouts', engine, if_exists='append', index=False)
    print(f"✅ Uploaded {len(df)} records from {csv_file} for month {month_tag}")
except Exception as e:
    print(f"❌ Upload failed: {e}")
