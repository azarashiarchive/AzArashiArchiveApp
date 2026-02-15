import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Azarashi Archive", page_icon="🎬", layout="wide")

# --- 1. CONNECTION SETUP ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. DATA LOADING ---
# Load Library (Dropdown options)
try:
    library_df = conn.read(worksheet="Library", ttl="10m")
    library_df.columns = library_df.columns.str.strip()
    file_options = library_df['File Name'].tolist()
except Exception as e:
    st.error(f"Error loading Library: {e}")
    file_options = []

# Load Requests (Live status board)
try:
    requests_df = conn.read(worksheet="Requests", ttl="2s")
    requests_df.columns = requests_df.columns.str.strip()
except Exception:
    requests_df = pd.DataFrame(columns=["User", "File", "Status", "Link", "Timestamp"])

# --- 3. MAIN INTERFACE ---
st.title("🎬 File Request Portal")
st.markdown("Select a file to request a GigaFile upload from the local server.")

with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        selected_file = st.selectbox("Choose a file:", file_options)
    with col2:
        user_email = st.text_input("Your Email:")

    if st.button("🚀 Request GigaFile Upload", use_container_width=True):
        if user_email and selected_file:
            try:
                # ---------------------------------------------------------
                # THE FIX: RECURSIVE CLIENT RETRIEVAL
                # ---------------------------------------------------------
                # We try the most common internal paths for the gspread client
                if hasattr(conn, "_instance") and hasattr(conn._instance, "_client"):
                    client = conn._instance._client
                elif hasattr(conn, "_instance") and hasattr(conn._instance, "_engine"):
                    client = conn._instance._engine.client
                else:
                    # Fallback for older/newer versions
                    client = conn._instance.client

                # Target your specific Spreadsheet ID
                spreadsheet_id = "1eKARMeobo9BI0nGIn8Nn9DbPrVnMs5tWGieX3Kzijds"
                
                # Open the sheet and the specific 'Requests' tab
                sh = client.open_by_key(spreadsheet_id)
                sheet = sh.worksheet("Requests")
                
                # Prepare data [User, File, Status, Link, Timestamp]
                timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = [user_email, selected_file, "Pending", "", timestamp]
                
                # Append to bottom
                sheet.append_row(new_row)
                
                st.success(f"✅ Request for '{selected_file}' logged!")
                st.balloons()
                st.cache_data.clear()
                st.rerun()
                
            except Exception as e:
                st.error(f"Detailed Logic Error: {e}")
                st.info("Check if Service Account is an 'Editor' on the Google Sheet.")
        else:
            st.warning("Please fill in both fields.")

# --- 4. LIVE STATUS BOARD ---
st.divider()
st.subheader("📋 Recent Requests")

if not requests_df.empty:
    # Show last 10 requests, newest at the top
    st.dataframe(
        requests_df.tail(10).iloc[::-1], 
        use_container_width=True,
        column_config={"Link": st.column_config.LinkColumn("Download Link")}
    )
else:
    st.info("Waiting for first request...")

if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()
