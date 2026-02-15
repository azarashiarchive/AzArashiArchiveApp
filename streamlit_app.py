import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- SETUP ---
st.set_page_config(page_title="File Request System")
# Create connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- LOAD DATA ---
# Read the "Library" tab for the dropdown
library_df = conn.read(worksheet="Library", usecols=[0, 1], ttl="10m") 
# Read the "Requests" tab to show status
requests_df = conn.read(worksheet="Requests", ttl="2s") # Short TTL to see updates fast

# --- UI: THE MENU ---
st.title("🎬 File Request Portal")

# 1. Select File
file_options = library_df['File Name'].tolist()
selected_file = st.selectbox("Choose a file:", file_options)
user_email = st.text_input("Your Email (for notification):")

# 2. Place Order
if st.button("Request File"):
    if user_email and selected_file:
        # Add a new row to the 'Requests' tab
        # We append a row with: [Email, File, Status, Link, Timestamp]
        new_row = pd.DataFrame([{
            "User": user_email,
            "File": selected_file,
            "Status": "Pending",
            "Link": "",
            "Timestamp": pd.Timestamp.now()
        }])
        
        # Append to sheet (This uses the simplified write mode)
        # Note: In production, you might use gspread for more precise appending
        updated_df = pd.concat([requests_df, new_row], ignore_index=True)
        conn.update(worksheet="Requests", data=updated_df)
        
        st.success("Request sent! The server is processing it.")
    else:
        st.error("Please fill in all fields.")

# --- UI: ORDER STATUS ---
st.divider()
st.subheader("📋 Live Status Board")
# Show the last 5 requests
st.dataframe(requests_df.tail(5))

if st.button("🔄 Refresh Status"):
    st.rerun()
