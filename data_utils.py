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
    all_draw_info = find_query_str()
    
    if not all_draw_info:
        st.warning("Failed to get query strings, will return empty list")
        return []
    
    st.success(f"Found {len(all_draw_info)} total query strings from the website")
    
    # Step 2: If we don't have any existing data, return all query strings
    if current_data is None or current_data.empty:
        st.info("No existing data, will fetch all query strings")
        return [info['query_string'] for info in all_draw_info]
    
    # Step 3: Check for duplicate draw numbers in the database
    st.subheader("Database Check")
    duplicate_rows = current_data[current_data.duplicated(subset=['draw_number'], keep=False)]
    if not duplicate_rows.empty:
        st.warning(f"Found {len(duplicate_rows)} duplicate entries in the database!")
        
        # Show the duplicates
        st.write("Sample of duplicate entries:")
        st.dataframe(duplicate_rows[['draw_date', 'draw_number']].head(10))
        
        # For diagnosis purposes, let's check what draw numbers are duplicated
        duplicate_numbers = duplicate_rows['draw_number'].unique()
        st.warning(f"Duplicate draw numbers: {sorted(duplicate_numbers)}")
        
        # Remove duplicates to get a clean list for comparison
        st.info("Will use de-duplicated database for comparison")
        current_data = current_data.drop_duplicates(subset=['draw_number'], keep='first')
        st.success(f"After de-duplication, database contains {len(current_data)} unique draws")
    
    # Get draw numbers from the database after de-duplication
    existing_draw_numbers = set(current_data['draw_number'].astype(int).tolist())
    
    # Display some debug info
    st.info(f"Database contains {len(existing_draw_numbers)} unique draw numbers")
    st.info(f"Earliest draw: {min(existing_draw_numbers)}, Latest draw: {max(existing_draw_numbers)}")
    
    # Debug: Show draw numbers in database for comparison
    if st.checkbox("Show all draw numbers in database"):
        st.json(sorted(list(existing_draw_numbers)))
    
    # Step 4: Filter out query strings for draws we already have in the database
    missing_query_strings = []
    
    # Keep track of how many were filtered due to existing in the database
    filtered_count = 0
    unmatched_count = 0
    added_count = 0
    
    # Show found draw numbers in query strings
    found_draw_numbers = {}
    
    # First pass: Decode all base64 draw numbers for visibility
    for draw_info in all_draw_info:
        query_string = draw_info['query_string']
        if query_string.startswith("sppl="):
            try:
                import base64
                import re
                encoded_part = query_string.split("=")[1]
                decoded = base64.b64decode(encoded_part).decode('utf-8')
                number_match = re.search(r'=(\d+)', decoded)
                if number_match:
                    draw_number = int(number_match.group(1))
                    found_draw_numbers[query_string] = draw_number
            except:
                # Silently continue if decoding fails
                pass
    
    if found_draw_numbers:
        st.info(f"Found {len(found_draw_numbers)} draw numbers from query strings")
        if st.checkbox("Show all decoded draw numbers"):
            st.json(found_draw_numbers)
        
        # Debugging: print out the overlap between existing and found draw numbers
        existing_set = set(existing_draw_numbers)
        found_set = set(found_draw_numbers.values())
        overlap = existing_set.intersection(found_set)
        st.info(f"Overlap between database and query strings: {len(overlap)} draw numbers")
        
        # Verify that draws we think exist really do exist
        if st.checkbox("Verify draw numbers"):
            st.info("Checking first 10 draws...")
            for query, draw_num in list(found_draw_numbers.items())[:10]:
                if draw_num in existing_draw_numbers:
                    st.write(f"Draw #{draw_num} exists in database ✓")
                else:
                    st.write(f"Draw #{draw_num} is missing from database ✗")
    
    st.subheader("Filtering Query Strings")
    
    # Second pass: Actually filter query strings
    for draw_info in all_draw_info:
        query_string = draw_info['query_string']
        draw_number = draw_info['draw_number']
        draw_date = draw_info['draw_date']
        
        # If we already know the draw number from the decoded draw info
        if query_string in found_draw_numbers:
            extracted_draw_number = found_draw_numbers[query_string]
            
            # Check if this draw is already in our database
            if extracted_draw_number not in existing_draw_numbers:
                missing_query_strings.append(query_string)
                st.write(f"Adding draw #{extracted_draw_number} to fetch queue")
                added_count += 1
            else:
                filtered_count += 1
                # We don't show every skipped item to keep the output cleaner
                if filtered_count <= 5 or filtered_count % 20 == 0:
                    st.write(f"Skipping draw #{extracted_draw_number} (already in database)")
            
            # Continue to the next query string
            continue
        
        # If we have a draw number directly from draw_info
        if draw_number is not None:
            # We have a draw number, check if it's in our database
            if draw_number not in existing_draw_numbers:
                missing_query_strings.append(query_string)
                added_count += 1
            else:
                filtered_count += 1
        else:
            # No draw number available, try to extract it from query string
            try:
                if "id=" in query_string:
                    # Try to extract draw ID from id= parameter
                    draw_id = query_string.split("id=")[1].split("&")[0]
                    if draw_id.isdigit() and int(draw_id) not in existing_draw_numbers:
                        missing_query_strings.append(query_string)
                        added_count += 1
                    else:
                        filtered_count += 1
                elif query_string.startswith("sppl="):
                    # This is a fallback in case the first pass didn't catch it
                    try:
                        import base64
                        encoded_part = query_string.split("=")[1]
                        decoded = base64.b64decode(encoded_part).decode('utf-8')
                        
                        # Try to extract the draw number from the decoded string
                        import re
                        number_match = re.search(r'=(\d+)', decoded)
                        if number_match:
                            extracted_draw_number = int(number_match.group(1))
                            
                            # Check if this draw is already in our database
                            if extracted_draw_number not in existing_draw_numbers:
                                missing_query_strings.append(query_string)
                                st.write(f"Adding draw #{extracted_draw_number} to fetch queue (fallback method)")
                                added_count += 1
                            else:
                                filtered_count += 1
                        else:
                            # Couldn't extract draw number from base64, include to be safe
                            missing_query_strings.append(query_string)
                            unmatched_count += 1
                    except Exception as e:
                        # If base64 decoding fails, include to be safe
                        st.write(f"Failed to decode base64: {str(e)}")
                        missing_query_strings.append(query_string)
                        unmatched_count += 1
                else:
                    # If we can't determine the draw number, include it to be safe
                    missing_query_strings.append(query_string)
                    unmatched_count += 1
            except Exception as e:
                # If parsing fails, include it to be safe
                st.write(f"Error processing query string: {str(e)}")
                missing_query_strings.append(query_string)
                unmatched_count += 1
    
    st.info(f"Found {len(missing_query_strings)} query strings for draws not in the database")
    st.write(f"Added {added_count} missing draws, filtered out {filtered_count} existing draws")
    st.write(f"Included {unmatched_count} draws with unmatched IDs for safety")
    
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
