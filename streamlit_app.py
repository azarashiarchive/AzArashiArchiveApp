import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection  # <--- THIS IS THE MISSING PIECE
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
        # Ensure Timestamp is a datetime object
        req['Timestamp'] = pd.to_datetime(req['Timestamp'])
    except:
        req = pd.DataFrame(columns=["File", "Status", "Link", "Timestamp"])
    
    return lib, req

library_df, requests_df = load_and_merge_data()

# --- 3. SIDEBAR FILTERING ---
st.sidebar.header("🔍 Filter Archive")
all_categories = library_df['Category'].unique().tolist() if 'Category' in library_df.columns else []
selected_cat = st.sidebar.multiselect("Category", all_categories, default=all_categories)

search_query = st.sidebar.text_input("Search Filename", "")

# Apply Filters
filtered_df = library_df.copy()
if selected_cat:
    filtered_df = filtered_df[filtered_df['Category'].isin(selected_cat)]
if search_query:
    filtered_df = filtered_df[filtered_df['File Name'].str.contains(search_query, case=False)]

# --- 4. MAIN INTERFACE ---
st.title("🎬 Azarashi Archive Explorer")
st.write(f"Showing {len(filtered_df)} files available in the vault.")

# --- 5. THE DYNAMIC TABLE ---
# We build a custom display loop to handle the logic per row
st.divider()

# Table Header
h1, h2, h3, h4 = st.columns([3, 2, 2, 2])
h1.write("**Filename**")
h2.write("**Status / Link**")
h3.write("**Expires In**")
h4.write("**Action**")
st.divider()

for _, row in filtered_df.iterrows():
    filename = row['File Name']
    
    # Find the latest SUCCESSFUL request for this file
    file_requests = requests_df[(requests_df['File'] == filename) & (requests_df['Status'] == 'Done')]
    
    last_req_time = None
    giga_link = "N/A"
    
    if not file_requests.empty:
        latest = file_requests.sort_values('Timestamp', ascending=False).iloc[0]
        last_req_time = latest['Timestamp']
        giga_link = latest['Link']

    # Calculate Expiration
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

    # Render Row
    r1, r2, r3, r4 = st.columns([3, 2, 2, 2])
    
    r1.write(filename)
    
    if not is_expired:
        r2.link_button("🔗 Download File", giga_link)
        r3.write(countdown_text)
        r4.write("✅ Active")
    else:
        r2.write("⚠️ Link Unavailable")
        r3.write(countdown_text)
        # REQUEST BUTTON
        if r4.button("🚀 Request", key=f"req_{filename}"):
            try:
                # Same gspread logic as before
                client = conn._instance._client if hasattr(conn._instance, '_client') else conn._instance.client
                spreadsheet_id = "1eKARMeobo9BI0nGIn8Nn9DbPrVnMs5tWGieX3Kzijds"
                sh = client.open_by_key(spreadsheet_id)
                sheet = sh.worksheet("Requests")
                
                new_row = [filename, "Pending", "", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                sheet.append_row(new_row)
                
                st.toast(f"Request sent for {filename}!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.write("---")
