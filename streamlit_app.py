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
    # We set a very low TTL (Time To Live) so the user sees the 'Done' status quickly
    requests_df = conn.read(worksheet="Requests", ttl="2s")
    requests_df.columns = requests_df.columns.str.strip()
except Exception:
    # Fallback if the Requests sheet is empty or not found
    requests_df = pd.DataFrame(columns=["File", "Status", "Link", "Timestamp"])

# --- 3. MAIN INTERFACE ---
st.title("🎬 File Request Portal")
st.markdown("Select a file to request a GigaFile upload. Monitor the table below for your download link.")

with st.container(border=True):
    # Only one input needed now
    selected_file = st.selectbox("Select the file you want to download:", file_options)

    if st.button("🚀 Request GigaFile Upload", use_container_width=True):
        if selected_file:
            try:
                # RECURSIVE CLIENT RETRIEVAL (To handle library versioning)
                if hasattr(conn, "_instance") and hasattr(conn._instance, "_client"):
                    client = conn._instance._client
                elif hasattr(conn, "_instance") and hasattr(conn._instance, "_engine"):
                    client = conn._instance._engine.client
                else:
                    client = conn._instance.client

                # Target your specific Spreadsheet ID
                spreadsheet_id = "1eKARMeobo9BI0nGIn8Nn9DbPrVnMs5tWGieX3Kzijds"
                
                sh = client.open_by_key(spreadsheet_id)
                sheet = sh.worksheet("Requests")
                
                # Prepare data [File, Status, Link, Timestamp]
                # Note: 'User/Email' column is removed
                timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = [selected_file, "Pending", "", timestamp]
                
                # Append to bottom of sheet
                sheet.append_row(new_row)
                
                st.success(f"✅ Request for '{selected_file}' added to the queue!")
                st.balloons()
                st.cache_data.clear()
                st.rerun()
                
            except Exception as e:
                st.error(f"Logic Error: {e}")
                st.info("Ensure the Service Account is an 'Editor' and the Google Drive API is enabled.")
        else:
            st.warning("Please select a file first.")

# --- 4. LIVE STATUS BOARD ---
st.divider()
st.subheader("📋 Live Download Queue")
st.info("Once the status changes to 'Done', click the link in the 'Download Link' column.")

if not requests_df.empty:
    # Clean the dataframe for display (Removing 'User' column if it still exists in the sheet)
    display_cols = ["File", "Status", "Link", "Timestamp"]
    # Only show columns that actually exist in the dataframe
    existing_cols = [c for c in display_cols if c in requests_df.columns]
    
    # Show last 15 requests, newest at the top
    st.dataframe(
        requests_df[existing_cols].tail(15).iloc[::-1], 
        use_container_width=True,
        hide_index=True,
        column_config={
            "Link": st.column_config.LinkColumn("Download Link", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Timestamp": st.column_config.TextColumn("Time Requested", width="small")
        }
    )
else:
    st.write("No active requests. Select a file above to start.")

if st.button("🔄 Check for Updates"):
    st.cache_data.clear()
    st.rerun()
