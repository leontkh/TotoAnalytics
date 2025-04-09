import pandas as pd
import pickle
import os
from datetime import datetime, timedelta

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

def get_missing_draw_dates(current_data):
    """
    Determine draw dates that are missing from our database
    
    Args:
        current_data: DataFrame containing current TOTO results
    
    Returns:
        List of dates to scrape (in 'YYYY-MM-DD' format)
    """
    # TOTO draws typically happen on Monday and Thursday
    # Here we'll construct a list of dates going back 3 months (90 days)
    # and check which ones we don't have in our database
    
    today = datetime.now().date()
    three_months_ago = today - timedelta(days=90)
    
    # Get all Mondays and Thursdays in the date range
    dates_to_check = []
    current_date = three_months_ago
    
    while current_date <= today:
        # 0 is Monday, 3 is Thursday
        if current_date.weekday() == 0 or current_date.weekday() == 3:
            dates_to_check.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    
    # If we don't have any data yet, return all dates to check
    if current_data is None or current_data.empty:
        return dates_to_check
    
    # Convert draw_date in current_data to string format if it's not already
    if pd.api.types.is_datetime64_any_dtype(current_data['draw_date']):
        existing_dates = set(current_data['draw_date'].dt.strftime('%Y-%m-%d'))
    else:
        existing_dates = set(current_data['draw_date'])
    
    # Find dates that we don't have in our database
    missing_dates = [date for date in dates_to_check if date not in existing_dates]
    
    return missing_dates

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
