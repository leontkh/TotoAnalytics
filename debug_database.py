import pandas as pd
import pickle
import os

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

def analyze_database():
    """
    Print information about the database to help with debugging
    """
    db = load_database()
    
    if db is None:
        print("No database file found.")
        return
    
    print(f"Database contains {len(db)} entries")
    print(f"Date range: {db['draw_date'].min()} to {db['draw_date'].max()}")
    
    # Check for draw numbers
    print(f"Database contains draws from #{db['draw_number'].min()} to #{db['draw_number'].max()}")
    print(f"Number of unique draw numbers: {db['draw_number'].nunique()}")
    
    # Show a few examples
    print("\nFirst 5 entries:")
    print(db[['draw_date', 'draw_number']].head())
    
    print("\nLast 5 entries:")
    print(db[['draw_date', 'draw_number']].tail())
    
    # Check for duplicates
    duplicate_draws = db[db.duplicated(subset=['draw_number'], keep=False)]
    if not duplicate_draws.empty:
        print("\nDuplicate draw numbers found:")
        print(duplicate_draws[['draw_date', 'draw_number']])
    else:
        print("\nNo duplicate draw numbers found.")
    
    # Print a list of all draw numbers for manual verification
    draw_numbers = sorted(db['draw_number'].unique())
    print(f"\nAll unique draw numbers: {draw_numbers}")

if __name__ == "__main__":
    analyze_database()