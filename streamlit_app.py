import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Azarashi Archive", page_icon="🎬", layout="wide")

# --- 1. CONNECTION SETUP ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. DATA LOADING & PREP ---
@st.cache_data(ttl="2s")
def load_and_merge_data():
    # Load Library
    lib = conn.read(worksheet="Library")
    lib.columns = lib.columns.str.strip()
    
    # Load Requests
    try:
        req = conn.read(worksheet="Requests")
        req.columns = req.columns.str.strip()
        # Ensure Timestamp is a datetime object for math
        req['Timestamp'] = pd.to_datetime(req['Timestamp'])
    except:
        # Fallback if Requests sheet is empty
        req = pd.DataFrame(columns=["File", "Status", "Link", "Timestamp"])
    
    return lib, req

library_df, requests_df = load_and_merge_data()

# --- 3. SIDEBAR DUAL-CATEGORY FILTERING ---
st.sidebar.header("🔍 Filter Archive")

# Filter 1: Type (Movie, Drama, TV Show)
# We pull unique values from the sheet, but you can hardcode them too
type_options = library_df['Type'].unique().tolist() if 'Type' in library_df.columns else ["Movie", "Drama", "TV Show"]
selected_types = st.sidebar.multiselect("Category 1: Type", type_options)

# Filter 2: Names (Name 1, Name 2, etc.)
name_options = library_df['Actor'].unique().tolist() if 'Actor' in library_df.columns else ["Name 1", "Name 2", "Name 3"]
selected_names = st.sidebar.multiselect("Category 2: Person", name_options)

search_query = st.sidebar.text_input("Search Filename", "")

# --- APPLY FILTER LOGIC ---
filtered_df = library_df.copy()

# Filter by Category 1 if any selected
if selected_types:
    filtered_df = filtered_df[filtered_df['Type'].isin(selected_types)]

# Filter by Category 2 if any selected
if selected_names:
    filtered_df = filtered_df[filtered_df['Actor'].isin(selected_names)]

# Filter by search query if text entered
if search_query:
    filtered_df = filtered_df[filtered_df['File Name'].str.contains(search_query, case=False)]

# --- 4. MAIN INTERFACE ---
st.title("🎬 Azarashi Archive Explorer")
st.write(f"Showing **{len(filtered_df)}** files available.")

# --- 5. THE DYNAMIC TABLE ---
st.divider()

# Header layout
h1, h2, h3, h4 = st.columns([3, 2, 2, 2])
h1.markdown("**Filename**")
h2.markdown("**Status / Link**")
h3.markdown("**Expires In**")
h4.markdown("**Action**")
st.divider()

for _, row in filtered_df.iterrows():
    filename = row['File Name']
    
    # Find the latest SUCCESSFUL request for this file
    file_requests = requests_df[(requests_df['File'] == filename) & (requests_df['Status'] == 'Done')]
    
    last_req_time = None
    giga_link = ""
    
    if not file_requests.empty:
        # Get the absolute latest entry
        latest = file_requests.sort_values('Timestamp', ascending=False).iloc[0]
        last_req_time = latest['Timestamp']
        giga_link = latest['Link']

    # Countdown Logic (100 days)
    is_expired = True
    countdown_text = "Never Requested"
    
    if last_req_time:
        expiry_date = last_req_time + timedelta(days=100)
        remaining = expiry_date - datetime.now()
        
        if remaining.days > 0:
            is_expired = False
            countdown_text = f"⏳ {remaining.days} Days"
        else:
            countdown_text = "❌ Expired"

    # --- RENDER THE ROW ---
    r1, r2, r3, r4 = st.columns([3, 2, 2, 2])
    
    r1.write(filename)
    
    if not is_expired and giga_link:
        r2.link_button("🔗 Download", giga_link, use_container_width=True)
        r3.write(countdown_text)
        r4.write("✅ Active")
    else:
        r2.write("⚠️ Link Expired/Missing")
        r3.write(countdown_text)
        
        # Action Button: Request Upload
        if r4.button("🚀 Request", key=f"btn_{filename}"):
            try:
                # Get client through nested instance
                client = conn._instance._client if hasattr(conn._instance, '_client') else conn._instance.client
                spreadsheet_id = "1eKARMeobo9BI0nGIn8Nn9DbPrVnMs5tWGieX3Kzijds"
                
                sh = client.open_by_key(spreadsheet_id)
                sheet = sh.worksheet("Requests")
                
                # [File, Status, Link, Timestamp]
                new_data = [filename, "Pending", "", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                sheet.append_row(new_data)
                
                st.toast(f"Request added for {filename}")
                st.rerun()
            except Exception as e:
                st.error(f"Request failed: {e}")

    st.divider()

