import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Set Streamlit Page Config
st.set_page_config(page_title="📊 US Index Options Dashboard", layout="wide")
st.title("📈 US Index Options Chain Dashboard")

# Sidebar Header
st.sidebar.header("🔽 Select Inputs")

# Fetch US indices with options data
@st.cache_data
def get_all_us_indices_with_options():
    common_us_indices = [
        "^SPX", "^NDX", "^DJI", "^RUT", "^VIX", "^OEX", "^XAX",
        "^NYA", "^MID", "^SML", "^GSPC", "^IXIC", "^TRAN",
        "^UTIL", "^SOX", "^RUA", "^W5000"
    ]
    
    valid_indices = []
    for index in common_us_indices:
        try:
            ticker = yf.Ticker(index)
            if ticker.options:
                valid_indices.append(index)
        except:
            continue
    return valid_indices

valid_indices = get_all_us_indices_with_options()
index_option = st.sidebar.selectbox("📊 Select a US Index", valid_indices, index=0)

# Fetch Expiry Dates
@st.cache_data
def fetch_expiry_dates(index):
    try:
        ticker = yf.Ticker(index)
        return ticker.options if ticker.options else []
    except:
        return []

expiry_dates = fetch_expiry_dates(index_option)

# Define fetch_option_chain() function
@st.cache_data
def fetch_option_chain(index, expiry):
    try:
        ticker = yf.Ticker(index)
        chain = ticker.option_chain(expiry)
        
        # Extract Calls and Puts Data
        calls = chain.calls.copy()
        puts = chain.puts.copy()
        
        # Add Expiry & Last Trade Date Column
        calls["expirationDate"] = expiry
        puts["expirationDate"] = expiry
        calls["lastTradeDate"] = pd.Timestamp.today().date()
        puts["lastTradeDate"] = pd.Timestamp.today().date()
        
        # Fill NaN values with 0
        calls.fillna(0, inplace=True)
        puts.fillna(0, inplace=True)
        
        return calls, puts
    except Exception as e:
        st.warning(f"Failed to fetch options data for {expiry}: {e}")
        return None, None

# Fetch only valid expiration dates with Open Interest > 0
valid_expiry_dates = []
for expiry in expiry_dates:
    calls_df, puts_df = fetch_option_chain(index_option, expiry)
    if calls_df is not None and puts_df is not None:
        options_df = pd.concat([calls_df, puts_df], ignore_index=True)
        if "openInterest" in options_df.columns and options_df["openInterest"].sum() > 0:
            valid_expiry_dates.append(expiry)

# User selects expiration date from filtered values
if valid_expiry_dates:
    selected_expiry = st.sidebar.selectbox("📅 Select Expiration Date", valid_expiry_dates, index=0)
else:
    st.error("No expiration dates available with open interest > 0")
    st.stop()

# Fetch and Filter Option Chain Data
calls_df, puts_df = fetch_option_chain(index_option, selected_expiry)

if calls_df is not None and puts_df is not None:
    # Ensure 'type' column exists before merging
    calls_df["type"] = "call"
    puts_df["type"] = "put"
    
    options_df = pd.concat([calls_df, puts_df], ignore_index=True)

    # Ensure 'openInterest' column exists before filtering
    if "openInterest" in options_df.columns:
        filtered_df = options_df[(options_df["openInterest"] > 0) & (options_df["expirationDate"] == selected_expiry)]
    else:
        st.error("Error: 'openInterest' column not found in data.")
        st.stop()
else:
    st.error("Error: Unable to fetch options chain data.")
    st.stop()

# Get Latest Last Price for Vertical Dashed Line (Renamed to "Current Price")
if not filtered_df.empty:
    current_price = filtered_df.loc[filtered_df["lastTradeDate"].idxmax(), "lastPrice"]
else:
    st.error("No data available after filtering. Please select another expiration date.")
    st.stop()

# Generate Interactive Plot with Plotly
fig = go.Figure()

# Add Call Options (Pink)
filtered_calls = filtered_df[filtered_df["type"] == "call"]
fig.add_trace(go.Bar(
    x=filtered_calls["strike"],
    y=filtered_calls["openInterest"],
    marker_color="pink",
    name="Call Options"
))

# Add Put Options (Blue)
filtered_puts = filtered_df[filtered_df["type"] == "put"]
fig.add_trace(go.Bar(
    x=filtered_puts["strike"],
    y=filtered_puts["openInterest"],
    marker_color="blue",
    name="Put Options"
))

# Add Vertical Dashed Line for Current Price
fig.add_trace(go.Scatter(
    x=[current_price, current_price],
    y=[0, max(filtered_df["openInterest"])],
    mode="lines",
    line=dict(color="black", dash="dash"),
    name=f"Current Price: {current_price:.2f}"
))

# Layout Customizations
fig.update_layout(
    title=f"Open Interest for {selected_expiry}",
    xaxis_title="Strike Prices",
    yaxis_title="Open Interest",
    barmode="group",
    xaxis=dict(
        type="category",
        tickangle=45,
        showgrid=True
    ),
    yaxis=dict(showgrid=True),
    hovermode="x unified"
)

# Display the Plot in Streamlit
st.plotly_chart(fig, use_container_width=True)

# Convert Filtered Data to CSV
csv_data = filtered_df.to_csv(index=False).encode('utf-8')

# Download Button for Filtered Data
st.download_button(
    label="📥 Download Filtered Data (CSV)",
    data=csv_data,
    file_name=f"{index_option}_options_{selected_expiry}.csv",
    mime='text/csv'
)
