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

def get_missing_query_strings(current_data=None):
    """
    Get a list of query strings to scrape from Singapore Pools website,
    filtering out draws that are already in the database
    
    Args:
        current_data: DataFrame containing current TOTO results
    
    Returns:
        List of query strings to use with scrape_toto_results
    """
    # Step 1: Get all available query strings from the Singapore Pools website
    st.info("Fetching available query strings from Singapore Pools website...")
    all_query_strings = find_query_str()
    
    if not all_query_strings:
        st.warning("Failed to get query strings, will return empty list")
        return []
    
    st.success(f"Found {len(all_query_strings)} total query strings from the website")
    
    # Step 2: If we don't have any existing data, return all query strings
    if current_data is None or current_data.empty:
        st.info("No existing data, will fetch all query strings")
        return all_query_strings
    
    # Step 3: Filter out query strings for draws we already have in the database
    # Extract draw numbers from the database
    existing_draw_numbers = set(current_data['draw_number'].astype(str).tolist())
    
    # Filter out query strings for draws we already have
    missing_query_strings = []
    
    for query_string in all_query_strings:
        # Extract draw number from query string (format usually contains draw_id=XXXX)
        try:
            # Example query string format: "/?page=toto-results&id=XXXX" or similar
            # Try to extract the ID from the query string
            if "id=" in query_string:
                draw_id = query_string.split("id=")[1].split("&")[0]
                
                # Check if this draw is already in our database
                if draw_id not in existing_draw_numbers:
                    missing_query_strings.append(query_string)
            else:
                # If we can't extract the ID, include it to be safe
                missing_query_strings.append(query_string)
        except Exception:
            # If parsing fails, include it to be safe
            missing_query_strings.append(query_string)
    
    st.info(f"Found {len(missing_query_strings)} query strings for draws not in the database")
    return missing_query_strings

def get_missing_draw_dates(current_data):
    """
    Determine query strings to use for draws missing from our database
    
    Args:
        current_data: DataFrame containing current TOTO results
    
    Returns:
        List of query strings to use with scrape_toto_results
    """
    # Use the enhanced function that filters out existing draws
    query_strings = get_missing_query_strings(current_data)
    
    # If we have query strings, return all of them
    if query_strings:
        st.info(f"Found {len(query_strings)} draws to fetch")
        return query_strings
    
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
