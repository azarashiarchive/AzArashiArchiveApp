import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Azarashi Archive", page_icon="🎬", layout="wide")

# --- 1. CONNECTION SETUP ---
# Connect using the secrets you've configured in Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. DATA LOADING ---
# Load Library (Cache for 10 minutes to keep it fast)
library_df = conn.read(worksheet="Library", ttl="10m")
library_df.columns = library_df.columns.str.strip() # Clean column names

# Load Requests (Cache for only 2 seconds so users see live updates)
# If this fails, we create an empty dataframe so the app doesn't crash
try:
    requests_df = conn.read(worksheet="Requests", ttl="2s")
    requests_df.columns = requests_df.columns.str.strip()
except Exception:
    requests_df = pd.DataFrame(columns=["User", "File", "Status", "Link", "Timestamp"])

# --- 3. MAIN INTERFACE ---
st.title("🎬 File Request Portal")
st.markdown("Select a file from the archive to request a GigaFile upload.")

# --- 4. SELECTION FORM ---
with st.container(border=True):
    col1, col2 = st.columns(2)
    
    with col1:
        file_options = library_df['File Name'].tolist()
        selected_file = st.selectbox("Choose a file:", file_options)
    
    with col2:
        user_email = st.text_input("Your Email (for notification):", placeholder="yourname@email.com")

if st.button("🚀 Request GigaFile Upload", use_container_width=True):
    if user_email and selected_file:
       try:
            # 1. Get the underlying gspread client correctly
            # In newer versions of the library, it's stored here:
            client = conn._instance.client 
            
            # 2. Get the Spreadsheet ID from your secrets
            # This ensures we are opening the exact right file
            spreadsheet_id = st.secrets["connections"]["gsheets"]["spreadsheet"].split("/")[-2]
            
            # 3. Open the sheet and the tab
            sh = client.open_by_key(spreadsheet_id)
            sheet = sh.worksheet("Requests")
            
            # 4. Prepare data row
            timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = [user_email, selected_file, "Pending", "", timestamp]
            
            # 5. Append
            sheet.append_row(new_row)
            
            st.success(f"✅ Request for '{selected_file}' logged!")
            st.cache_data.clear()
            st.rerun()
            
        except Exception as e:
            st.error(f"Detailed Logic Error: {e}")
    else:
        st.warning("Please fill in all fields.")

# --- 5. LIVE STATUS BOARD ---
st.divider()
st.subheader("📋 Recent Requests & Status")

if not requests_df.empty:
    # Filter/Sort to show newest requests first
    display_df = requests_df.tail(10).iloc[::-1] 
    st.dataframe(
        display_df, 
        use_container_width=True, 
        column_config={
            "Link": st.column_config.LinkColumn("Download Link"),
            "Timestamp": st.column_config.DatetimeColumn("Requested At")
        }
    )
else:
    st.info("No requests found yet. Be the first!")

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()
