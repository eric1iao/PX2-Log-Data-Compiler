import streamlit as st
import pandas as pd
from datetime import datetime
import re
import io

def parse_log_file(uploaded_file, source_label):
    pattern = re.compile(r'^(\d{4}-\d{2}-\d{2}T[^\s]+)\s+(.*)')
    entries = []

    for line in uploaded_file:
        line = line.decode('utf-8', errors='ignore')
        match = pattern.match(line)
        if match:
            timestamp_str, message = match.groups()
            try:
                timestamp = pd.to_datetime(timestamp_str)
                entries.append((timestamp, message.strip(), source_label))
            except Exception:
                continue
    return entries

def merge_and_filter_logs(files, start_time_str, end_time_str, tool_id, log_levels):
    if len(files) != 2:
        return pd.DataFrame(columns=["Timestamp", "Message", "Source"])

    # Sources
    sources = ["workflow", "connections"]
    all_entries = []

    for file, label in zip(files, sources):
        all_entries.extend(parse_log_file(file, label))

    if not all_entries:
        return pd.DataFrame(columns=["Timestamp", "Message", "Source"])

    df = pd.DataFrame(all_entries, columns=["Timestamp", "Message", "Source"])
    df = df.sort_values(by="Timestamp").reset_index(drop=True)

    # Filter by time
    if start_time_str and end_time_str:
        try:
            start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
            end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()
            df = df[df["Timestamp"].apply(lambda x: start_time <= x.time() <= end_time)]
        except ValueError:
            st.error("Invalid time format. Use HH:MM:SS.")
            return pd.DataFrame()

    # Filter by tool ID if provided
    if tool_id:
        df = df[df["Message"].str.contains(tool_id, case=False, na=False)]

    # Filter by log levels if provided
    if log_levels:
        df = df[df["Message"].str.contains('|'.join(log_levels), case=False, na=False)]

    return df

# UI
st.set_page_config(page_title="Log Merger", layout="centered")
st.title("🔧 Merge & Filter Log Files")
st.markdown("Upload **two log files** to merge and filter them by time, tool ID, and log levels. Output is downloadable as Excel.")

uploaded_files = st.file_uploader("Upload two log files", type=["txt", "log"], accept_multiple_files=True)

col1, col2 = st.columns(2)
with col1:
    start_time = st.text_input("Start Time (HH:MM:SS)", value="")
with col2:
    end_time = st.text_input("End Time (HH:MM:SS)", value="")

tool_id = st.text_input("Tool ID (optional)", value="")

# Log levels multi-select
log_levels = st.multiselect(
    "Select Log Levels (optional)",
    options=["ERR", "INF", "DBG"],  # Specified log levels
    default=["INF"]  # Default selection
)

if st.button("Merge and Filter Logs"):
    if not uploaded_files or len(uploaded_files) != 2:
        st.error("Please upload exactly two log files.")
    else:
        with st.spinner("Processing logs..."):
            result_df = merge_and_filter_logs(uploaded_files, start_time, end_time, tool_id, log_levels)

        if result_df.empty:
            st.warning("No matching log entries found.")
        else:
            st.success(f"Merged and filtered {len(result_df)} log entries.")
            st.dataframe(result_df.head(100))
