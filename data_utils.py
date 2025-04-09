import pandas as pd
import pickle
import os
from datetime import datetime, timedelta
import streamlit as st
from scraper import find_query_str

def load_database():
    """
    Load the TOTO results database from a pickle file
    
    Returns:
        DataFrame containing TOTO results, or None if file doesn't exist
    """
    try:
        if os.path.exists('toto_database.pkl'):
            with open('toto_database.pkl', 'rb') as f:
                return pickle.load(f)
        return None
    except Exception as e:
        print(f"Error loading database: {str(e)}")
        return None

def save_database(df):
    """
    Save the TOTO results database to a pickle file
    
    Args:
        df: DataFrame containing TOTO results
    """
    try:
        with open('toto_database.pkl', 'wb') as f:
            pickle.dump(df, f)
    except Exception as e:
        print(f"Error saving database: {str(e)}")

def get_missing_query_strings():
    """
    Get a list of query strings to scrape from Singapore Pools website
    
    Returns:
        List of query strings to use with scrape_toto_results
    """
    st.info("Fetching available query strings from Singapore Pools website...")
    query_strings = find_query_str()
    
    if query_strings:
        st.success(f"Found {len(query_strings)} query strings from the website")
    else:
        st.warning("Failed to get query strings, will return empty list")
        query_strings = []
    
    return query_strings

def get_missing_draw_dates(current_data):
    """
    Determine query strings to use for draws missing from our database
    
    Args:
        current_data: DataFrame containing current TOTO results
    
    Returns:
        List of query strings to use with scrape_toto_results
    """
    # Get all available query strings
    query_strings = get_missing_query_strings()
    
    # If we don't have any data yet, return all query strings
    if current_data is None or current_data.empty:
        st.info(f"No existing data, will fetch all {len(query_strings)} query strings")
        return query_strings
    
    # If we have query strings, return the first 5 to start with (we'll implement deduplication later)
    if query_strings:
        batch_size = min(5, len(query_strings))
        st.info(f"Will fetch the first {batch_size} query strings")
        return query_strings[:batch_size]
    
    # Fall back to the old method if no query strings found
    st.warning("Failed to get query strings from website, falling back to calendar-based method...")
    # TOTO draws typically happen on Monday and Thursday
    # Here we'll construct a list of dates going back 3 months (90 days)
    today = datetime.now().date()
    three_months_ago = today - timedelta(days=90)
    
    # Get all Mondays and Thursdays in the date range (as a placeholder - these aren't query strings)
    available_dates = []
    current_date = three_months_ago
    
    while current_date <= today:
        # 0 is Monday, 3 is Thursday
        if current_date.weekday() == 0 or current_date.weekday() == 3:
            available_dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    
    st.info(f"Using calendar-based approach with {len(available_dates)} dates as placeholders")
    return []  # Return empty list since calendar dates aren't query strings

def format_winning_numbers(row):
    """
    Format winning numbers for display
    
    Args:
        row: DataFrame row
    
    Returns:
        String of formatted winning numbers
    """
    if isinstance(row['winning_numbers'], list):
        return ', '.join([str(num) for num in row['winning_numbers']]) + f" + {row['additional_number']}"
    return "N/A"
