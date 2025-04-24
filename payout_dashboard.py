import streamlit as st
import hashlib
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

# --- Password Hashing ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Simulated user database ---
USER_CREDENTIALS = {
    "admin": hash_password("letmein123"),
    "user": hash_password("user123"),
}

# --- Setup session state on first load ---
if "authentication_status" not in st.session_state:
    st.session_state.authentication_status = None
if "username" not in st.session_state:
    st.session_state.username = ""

# --- Login Form ---
if st.session_state.authentication_status != True:
    st.title("🔒 Creator Payout Dashboard Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if username in USER_CREDENTIALS and hash_password(password) == USER_CREDENTIALS[username]:
                st.session_state.authentication_status = True
                st.session_state.username = username
            else:
                st.session_state.authentication_status = False
                st.warning("Incorrect username or password.")

    # Stop app if not logged in
    st.stop()

# --- Load environment and connect to DB ---
load_dotenv()
db_url = os.getenv("SUPABASE_DB_URL")
engine = create_engine(db_url)

# --- UI Title ---
st.title(f"📊 Welcome {st.session_state.username} — Creator Payout Dashboard")

# --- Admin-only Upload Section ---
if st.session_state.username == "admin":
    with st.expander("📤 Upload Monthly Payout CSV", expanded=False):
        with st.form("upload_form"):
            uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
            upload_month = st.text_input("Enter month in format YYYY-MM (e.g., 2025-04)")
            submit_upload = st.form_submit_button("Upload")

            # CSV guidance
            st.info("""
            **Expected CSV columns:**

            `Author ID`, `User ID`, `Email ID`, `Phone number`, `Langauge`, `Amount`,  
            `TDS Applicability`, `TDS`, `Payable`, `Net Payable`, `Name`,  
            `Account Number`, `IFSC`, `Transaction ID`, `Transaction Date`

            ✅ Headers are case-insensitive and auto-cleaned (spaces → underscores).
            """)

            if submit_upload:
                if not uploaded_file or not upload_month:
                    st.error("Please upload a CSV and enter the month.")
                else:
                    with st.spinner("📤 Uploading and processing your file..."):
                        try:
                            df = pd.read_csv(uploaded_file)
                            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
                            df = df.rename(columns={
                                'email_id': 'email',
                                'phone_number': 'phone',
                                'langauge': 'language',
                                'tds_applicability': 'tds_applicable'
                            })

                            df['tds_applicable'] = df['tds_applicable'].astype(str).str.lower().map({'yes': True, 'no': False})

                            numeric_columns = ['amount', 'tds', 'payable', 'net_payable']
                            for col in numeric_columns:
                                if col in df.columns:
                                    df[col] = df[col].astype(str).str.replace(',', '').astype(float)

                            if 'transaction_date' in df.columns:
                                try:
                                    df['transaction_date'] = pd.to_datetime(df['transaction_date'], dayfirst=True).dt.date
                                except:
                                    st.warning("⚠️ Could not convert 'Transaction Date' — check format.")

                            df['month'] = upload_month
                            df.to_sql('payouts', engine, if_exists='append', index=False)
                            st.success(f"✅ Uploaded {len(df)} records for {upload_month}")
                        except Exception as e:
                            st.error(f"❌ Upload failed: {e}")


# --- Filter UI ---
st.sidebar.header("🔍 Search & Filters")
search_input = st.sidebar.text_input("Author ID / User ID / Email")

# Refresh button
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()

month_range = st.sidebar.multiselect(
    "Select Months",
    options=pd.date_range("2023-01-01", periods=36, freq="M").strftime('%Y-%m').tolist()
)

show_only_tds = st.sidebar.checkbox("Only TDS Deducted")
show_only_uncredited = st.sidebar.checkbox("Only Uncredited")

# --- Fetch & Filter Data ---
@st.cache_data(show_spinner=False)
def load_data():
    return pd.read_sql("SELECT * FROM payouts", engine)

df = load_data()

if search_input:
    search_input = search_input.lower()
    df = df[df.apply(lambda row: search_input in str(row['user_id']).lower()
                                  or search_input in str(row['email']).lower()
                                  or search_input in str(row['author_id']).lower(), axis=1)]

if month_range:
    df = df[df['month'].isin(month_range)]

if show_only_tds:
    df = df[df['tds'] > 0]

if show_only_uncredited:
    df = df[df['transaction_id'].isna() | (df['transaction_id'] == '')]

# --- Display Table ---
st.subheader("📋 Filtered Payout Records")
st.write(f"Total Records: {len(df)}")
# Show only selected columns in the dashboard
display_columns = ['user_id', 'amount', 'net_payable', 'transaction_id', 'transaction_date', 'month']
df_display = df[display_columns] if all(col in df.columns for col in display_columns) else df

st.dataframe(df_display)


# --- Chart: Net Payable by Month ---
if not df.empty:
    st.subheader("📈 Monthly Net Payable")
    try:
        chart_df = df.groupby('month')['net_payable'].sum().reset_index()
        chart_df['month'] = pd.to_datetime(chart_df['month'], format='%Y-%m')
        chart_df = chart_df.sort_values('month')
        st.line_chart(chart_df.set_index('month')['net_payable'])
    except Exception as e:
        st.warning("⚠️ Couldn't parse dates for chart.")

# --- Download Button ---
if not df.empty:
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download CSV", csv, "filtered_payouts.csv", "text/csv")

st.caption("Built with ❤️ using Streamlit")
