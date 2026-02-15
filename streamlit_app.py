import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# --- 1. PASSWORD GATEKEEPER ---
def check_password():
    """Returns True if the user had the correct password."""

    def password_entered():
        # Update this to your desired password
        if st.session_state["password"] == "five":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Clear password from memory
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Initial state: Show only the login box
        st.markdown("Welcome to the AZArashi Archive")
        st.text_input(
            "Please enter the password:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Wrong password state
        st.markdown("Welcome to the AZArashi Archive")
        st.text_input(
            "Please enter the password:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("❌ Incorrect password. Please try again.")
        return False
    else:
        # Password is correct
        return True

# --- 2. THE MAIN APPLICATION ---
# This block only runs if check_password() returns True
if check_password():
    
    # --- PAGE CONFIG ---
    st.set_page_config(page_title="Azarashi Archive", page_icon="🎬", layout="wide")

    # --- CONNECTION & DATA ---
    conn = st.connection("gsheets", type=GSheetsConnection)

    @st.cache_data(ttl="2s")
    def load_data():
        lib = conn.read(worksheet="Library")
        lib.columns = lib.columns.str.strip()
        try:
            req = conn.read(worksheet="Requests")
            req.columns = req.columns.str.strip()
            req['Timestamp'] = pd.to_datetime(req['Timestamp'])
        except:
            req = pd.DataFrame(columns=["File", "Status", "Link", "Timestamp"])
        return lib, req

    library_df, requests_df = load_data()

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("🔍 Filter Archive")
    
    # Category 1: Type
    type_options = library_df['Type'].unique().tolist() if 'Type' in library_df.columns else ["Movie", "Drama", "TV Show"]
    selected_types = st.sidebar.multiselect("Category 1: Type", type_options)

    # Category 2: Actor/Person
    name_options = library_df['Actor'].unique().tolist() if 'Actor' in library_df.columns else ["Name 1", "Name 2"]
    selected_names = st.sidebar.multiselect("Category 2: Person", name_options)

    search_query = st.sidebar.text_input("Search Filename", "")

    # Apply Filtering
    filtered_df = library_df.copy()
    if selected_types:
        filtered_df = filtered_df[filtered_df['Type'].isin(selected_types)]
    if selected_names:
        filtered_df = filtered_df[filtered_df['Actor'].isin(selected_names)]
    if search_query:
        filtered_df = filtered_df[filtered_df['File Name'].str.contains(search_query, case=False)]

    # --- MAIN UI ---
    st.title("🦭⛈️Azarashi Archive Explorer⛈️🦭")
    st.write(f"Total Files: **{len(filtered_df)}**")
    st.divider()

    # Header Row
    h1, h2, h3, h4 = st.columns([3, 2, 2, 2])
    h1.markdown("**Filename**")
    h2.markdown("**Status / Link**")
    h3.markdown("**Expires In**")
    h4.markdown("**Action**")
    st.divider()

    # Display Rows
    for _, row in filtered_df.iterrows():
        filename = row['File Name']
        
        # Check for active requests
        file_requests = requests_df[(requests_df['File'] == filename) & (requests_df['Status'] == 'Done')]
        
        last_req_time = None
        giga_link = ""
        
        if not file_requests.empty:
            latest = file_requests.sort_values('Timestamp', ascending=False).iloc[0]
            last_req_time = latest['Timestamp']
            giga_link = latest['Link']

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

        # Render Table Row
        r1, r2, r3, r4 = st.columns([3, 2, 2, 2])
        r1.write(filename)
        
        if not is_expired and giga_link:
            r2.link_button("🔗 Download", giga_link, use_container_width=True)
            r3.write(countdown_text)
            r4.write("✅ Active")
        else:
            r2.write("⚠️ Unavailable")
            r3.write(countdown_text)
            
            # Action Button
            if r4.button("🚀 Request", key=f"btn_{filename}"):
                try:
                    # Get gspread client
                    if hasattr(conn, "_instance") and hasattr(conn._instance, "_client"):
                        client = conn._instance._client
                    else:
                        client = conn._instance.client
                    
                    spreadsheet_id = "1eKARMeobo9BI0nGIn8Nn9DbPrVnMs5tWGieX3Kzijds"
                    sh = client.open_by_key(spreadsheet_id)
                    sheet = sh.worksheet("Requests")
                    
                    # Append new row
                    sheet.append_row([filename, "Pending", "", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                    
                    st.toast(f"Request added for {filename}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        st.divider()
