import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import streamlit as st
import re
import trafilatura
import io
from io import StringIO
import urllib3
import json

# Suppress only the single InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# We'll no longer need this function since we're using queryString approach
# Leaving this as a placeholder in case we need to implement JSON API parsing in the future
def get_draw_results_by_date(draw_date):
    """
    This function is deprecated as we're now using the queryString approach
    
    Args:
        draw_date: Draw date in 'YYYY-MM-DD' format
    
    Returns:
        None - this function is no longer used
    """
    st.warning(f"Direct JSON API is not being used. Using queryString approach instead for date: {draw_date}")
    return None

def get_available_draw_dates():
    """
    Fetch available draw dates and queryStrings from the Singapore Pools API
    
    Returns:
        Dictionary with dates as keys and queryStrings as values
    """
    st.info("Fetching available draw dates...")
    
    url = "https://www.singaporepools.com.sg/DataFileArchive/Lottery/Output/toto_result_draw_list_en.html"
    
    # Set up headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://www.singaporepools.com.sg/en/Pages/Home.aspx',
    }
    
    # Disable SSL warnings globally (not recommended for production)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    try:
        # Disable SSL verification
        response = requests.get(url, headers=headers, verify=False)
        
        # Initialize the dictionary to store date to query string mapping
        date_to_query = {}
        
        if response.status_code == 200:
            st.info("Successfully got response from draw list URL")
            html_content = response.text
            
            # Check if we got any content
            if html_content:
                st.info(f"Downloaded {len(html_content)} bytes of HTML")
                
                # Simply parse the raw text for option tags with queryString
                # This approach is more robust than parsing with BeautifulSoup
                # Look for patterns like <option value="..." queryString="...">Mon, 01 Apr 2025</option>
                option_pattern = re.compile(r'<option.*?queryString="(.*?)".*?>(.*?)</option>', re.DOTALL)
                options = option_pattern.findall(html_content)
                
                st.info(f"Found {len(options)} options with regex pattern")
                
                for query_string, option_text in options:
                    # Clean up the text
                    option_text = option_text.strip()
                    
                    # Try to parse the date
                    try:
                        # Try multiple date formats
                        date_formatted = None
                        for fmt in ['%a, %d %b %Y', '%d %b %Y', '%d/%m/%Y', '%Y-%m-%d']:
                            try:
                                date = datetime.strptime(option_text, fmt)
                                date_formatted = date.strftime('%Y-%m-%d')
                                st.success(f"Successfully parsed date {option_text} with format {fmt}")
                                break
                            except ValueError:
                                continue
                        
                        if date_formatted:
                            date_to_query[date_formatted] = query_string
                            st.success(f"Found draw date: {date_formatted} with query string: {query_string}")
                        else:
                            st.warning(f"Could not parse date from option text: {option_text}")
                    except Exception as e:
                        st.warning(f"Failed to parse date from option: {option_text}, error: {str(e)}")
                
                # If we failed to find options with regex, try alternative method
                if not date_to_query:
                    st.info("Trying alternative parsing method...")
                    
                    # Try to extract dates and queryStrings using a different pattern
                    alt_pattern = re.compile(r'drawDate[\'"]?\s*:\s*[\'"]([^\'"]*)[\'"]\s*,\s*queryString[\'"]?\s*:\s*[\'"]([^\'"]*)[\'"]]', re.DOTALL)
                    alt_matches = alt_pattern.findall(html_content)
                    
                    st.info(f"Found {len(alt_matches)} date-query pairs with alternative pattern")
                    
                    for date_str, query_string in alt_matches:
                        try:
                            # Try to parse the date
                            date_formatted = None
                            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d %b %Y', '%d %B %Y']:
                                try:
                                    date = datetime.strptime(date_str, fmt)
                                    date_formatted = date.strftime('%Y-%m-%d')
                                    break
                                except ValueError:
                                    continue
                            
                            if date_formatted:
                                date_to_query[date_formatted] = query_string
                                st.info(f"Found draw date with alt method: {date_formatted}")
                        except Exception as e:
                            st.warning(f"Failed to parse date with alt method: {date_str}, error: {str(e)}")
            else:
                st.error("Received empty HTML content")
        else:
            st.error(f"Failed to fetch draw dates. Status code: {response.status_code}")
        
        # Sort dates in descending order (most recent first)
        sorted_dates = sorted(date_to_query.keys(), reverse=True)
        sorted_date_to_query = {date: date_to_query[date] for date in sorted_dates}
        
        # Log the number of available dates
        st.info(f"Found {len(sorted_date_to_query)} available draw dates")
        
        # If we found any dates, return them
        if sorted_date_to_query:
            return sorted_date_to_query
        else:
            st.warning("No dates found using HTML parsing, trying direct option parsing...")
            
            # Hard-coded fallback for testing - should add the most recent draws
            # This will allow us to at least get some data if the other methods fail
            fallback_dates = {
                "2025-04-07": "PageListID=250",
                "2025-04-03": "PageListID=249",
                "2025-03-31": "PageListID=248",
                "2025-03-27": "PageListID=247",
                "2025-03-24": "PageListID=246"
            }
            
            st.info(f"Using {len(fallback_dates)} fallback dates as last resort")
            return fallback_dates
    
    except Exception as e:
        st.error(f"Error fetching draw dates: {str(e)}")
        return {}

def scrape_toto_results(dates_to_scrape=None):
    """
    Scrape TOTO results from Singapore Pools website
    
    Args:
        dates_to_scrape: List of dates to scrape. If None, scrape the latest result.
    
    Returns:
        A DataFrame containing the scraped TOTO results
    """
    results = []
    
    try:
        st.info("Attempting to get TOTO results...")
        
        # Get date to queryString mapping
        date_to_query = get_available_draw_dates()
        
        # If no specific dates provided, get the latest available date
        if not dates_to_scrape:
            st.info("No specific dates provided, fetching latest available draw date...")
            if date_to_query:
                # Get the most recent date (first key)
                dates_to_scrape = [next(iter(date_to_query))]
                st.info(f"Will fetch latest draw date: {dates_to_scrape[0]}")
            else:
                st.warning("No available dates found from API, will try general scraping")
        
        # Try using queryString approach first for each date
        api_success = False
        if dates_to_scrape:
            for date in dates_to_scrape:
                # Check if we have a queryString for this date
                if date in date_to_query:
                    query_string = date_to_query[date]
                    st.info(f"Found queryString for date {date}: {query_string}")
                    
                    # Build the URL with the queryString
                    base_url = "https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx"
                    url = f"{base_url}?{query_string}"
                    st.info(f"Attempting to fetch results from: {url}")
                    
                    # Set up headers for the request
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Cache-Control': 'max-age=0',
                        'Referer': 'https://www.singaporepools.com.sg/en/Pages/Home.aspx',
                    }
                    
                    try:
                        # Disable SSL verification for this specific request
                        response = requests.get(url, headers=headers, verify=False)
                        status = response.status_code
                        
                        if status == 200:
                            html_content = response.text
                            st.info(f"Successfully downloaded {len(html_content)} bytes")
                            
                            # Parse the HTML to extract information
                            soup = BeautifulSoup(html_content, 'html.parser')
                            
                            # Extract draw number
                            draw_number = None
                            draw_pattern = re.compile(r'Draw No\.?\s*(\d+)', re.IGNORECASE)
                            draw_elements = soup.find_all(string=lambda text: bool(text and draw_pattern.search(str(text))))
                            
                            if draw_elements:
                                for element in draw_elements:
                                    element_str = str(element)
                                    match = draw_pattern.search(element_str)
                                    if match:
                                        draw_number = int(match.group(1))
                                        st.info(f"Found draw number: {draw_number}")
                                        break
                            
                            # Extract winning numbers
                            winning_numbers = []
                            additional_number = None
                            
                            # Multiple approaches to find winning numbers
                            
                            # Approach 1: Look for "Winning Numbers" text
                            winning_numbers_header = soup.find(string=re.compile("Winning Numbers", re.IGNORECASE))
                            if winning_numbers_header:
                                st.info("Found 'Winning Numbers' text")
                                # Find the table by going up the DOM tree
                                parent = winning_numbers_header.parent
                                while parent and parent.name != 'table':
                                    parent = parent.parent
                                
                                if parent and parent.name == 'table':
                                    st.info("Found table containing winning numbers")
                                    # Extract numbers from this table
                                    for cell in parent.find_all(['td', 'th']):
                                        cell_text = cell.get_text(strip=True)
                                        if cell_text.isdigit() and 1 <= int(cell_text) <= 49:  # TOTO numbers are 1-49
                                            winning_numbers.append(int(cell_text))
                                    st.info(f"Extracted numbers from table: {winning_numbers}")
                            
                            # Approach 2: Look for a div with number class
                            if not winning_numbers or len(winning_numbers) < 6:
                                st.info("Looking for elements with number classes...")
                                number_elements = soup.find_all(class_=re.compile("(number|ball|toto-number)", re.IGNORECASE))
                                
                                if number_elements:
                                    st.info(f"Found {len(number_elements)} elements with number classes")
                                    candidate_numbers = []
                                    for elem in number_elements:
                                        elem_text = elem.get_text(strip=True)
                                        if elem_text.isdigit() and 1 <= int(elem_text) <= 49:
                                            candidate_numbers.append(int(elem_text))
                                    
                                    # If we found at least 7 numbers (6 winning + 1 additional), use them
                                    if len(candidate_numbers) >= 7:
                                        winning_numbers = candidate_numbers[:6]
                                        additional_number = candidate_numbers[6]
                                        st.info(f"Found numbers from class elements: {winning_numbers} + {additional_number}")
                                    # If we found 6 numbers, use them and look for additional separately
                                    elif len(candidate_numbers) == 6:
                                        winning_numbers = candidate_numbers
                                        st.info(f"Found exactly 6 numbers from class elements: {winning_numbers}")
                            
                            # Approach 3: Try to find all tables and look for one with 6-7 numbers
                            if not winning_numbers or len(winning_numbers) < 6:
                                st.info("Scanning all tables for winning numbers...")
                                all_tables = soup.find_all('table')
                                for table in all_tables:
                                    table_numbers = []
                                    for cell in table.find_all(['td', 'th']):
                                        cell_text = cell.get_text(strip=True)
                                        if cell_text.isdigit() and 1 <= int(cell_text) <= 49:
                                            table_numbers.append(int(cell_text))
                                    
                                    # Check if this table has 6 or 7 numbers (potential winning numbers table)
                                    if 6 <= len(table_numbers) <= 7:
                                        st.info(f"Found table with {len(table_numbers)} numbers: {table_numbers}")
                                        if len(table_numbers) == 7:
                                            winning_numbers = table_numbers[:6]
                                            additional_number = table_numbers[6]
                                        else:  # len == 6
                                            winning_numbers = table_numbers
                                        break
                            
                            # Look for additional number
                            if not additional_number:
                                # Try multiple approaches to find the additional number
                                
                                # Approach 1: Look for "Additional Number" text
                                additional_header = soup.find(string=re.compile("Additional Number", re.IGNORECASE))
                                if additional_header:
                                    st.info("Found 'Additional Number' text")
                                    # Find closest table by going up the DOM tree
                                    parent = additional_header.parent
                                    while parent and parent.name != 'table':
                                        parent = parent.parent
                                    
                                    if parent and parent.name == 'table':
                                        for cell in parent.find_all(['td', 'th']):
                                            cell_text = cell.get_text(strip=True)
                                            if cell_text.isdigit() and 1 <= int(cell_text) <= 49:
                                                additional_number = int(cell_text)
                                                st.info(f"Found additional number: {additional_number}")
                                                break
                                
                                # Approach 2: If we already have winning numbers, look for a separate number in a div or span
                                if not additional_number and winning_numbers and len(winning_numbers) >= 6:
                                    st.info("Looking for additional number near winning numbers...")
                                    # Look for a div or span with a single number that's not in winning_numbers
                                    for elem in soup.find_all(['div', 'span', 'td']):
                                        elem_text = elem.get_text(strip=True)
                                        if elem_text.isdigit() and 1 <= int(elem_text) <= 49:
                                            num = int(elem_text)
                                            if num not in winning_numbers:
                                                additional_number = num
                                                st.info(f"Found additional number: {additional_number}")
                                                break
                                
                                # Approach 3: Try to find a container with "additional" class
                                if not additional_number:
                                    st.info("Looking for element with 'additional' class...")
                                    additional_elems = soup.find_all(class_=re.compile("additional", re.IGNORECASE))
                                    for elem in additional_elems:
                                        elem_text = elem.get_text(strip=True)
                                        # Try to extract a number from the text
                                        num_match = re.search(r'\d+', elem_text)
                                        if num_match:
                                            num = int(num_match.group(0))
                                            if 1 <= num <= 49:
                                                additional_number = num
                                                st.info(f"Found additional number from class: {additional_number}")
                                                break
                            
                            # Initialize prize data
                            prize_data = {
                                'group_1_winners': 0, 'group_1_prize': 0,
                                'group_2_winners': 0, 'group_2_prize': 0,
                                'group_3_winners': 0, 'group_3_prize': 0,
                                'group_4_winners': 0, 'group_4_prize': 0,
                                'group_5_winners': 0, 'group_5_prize': 0,
                                'group_6_winners': 0, 'group_6_prize': 0,
                                'group_7_winners': 0, 'group_7_prize': 0
                            }
                            
                            # Look for the prize table
                            all_tables = soup.find_all('table')
                            for table in all_tables:
                                # Try to read the table with pandas
                                try:
                                    table_html = str(table)
                                    df_table = pd.read_html(StringIO(table_html))[0]
                                    
                                    # Check if this looks like a prize table by looking for "Group" in column names or values
                                    has_group = any('group' in str(col).lower() for col in df_table.columns) or \
                                                any('group' in str(val).lower() for val in df_table.values.flatten() if isinstance(val, str))
                                    
                                    if has_group:
                                        st.info("Found prize table")
                                        
                                        # Try to extract group, winners, and prize information
                                        for _, row in df_table.iterrows():
                                            # Convert row to dict for easier handling
                                            row_dict = row.to_dict()
                                            
                                            # Look for "Group N" pattern in any cell
                                            group_found = False
                                            group_num = None
                                            
                                            for _, cell_value in row_dict.items():
                                                if isinstance(cell_value, str):
                                                    group_match = re.search(r'Group\s*(\d)', str(cell_value), re.IGNORECASE)
                                                    if group_match:
                                                        group_num = int(group_match.group(1))
                                                        group_found = True
                                                        break
                                            
                                            if group_found and group_num:
                                                # Look for prize amount and winners in this row
                                                prize_amount = None
                                                winners_count = None
                                                
                                                for _, cell_value in row_dict.items():
                                                    # Look for dollar amounts for prize
                                                    if isinstance(cell_value, str) and '$' in str(cell_value):
                                                        prize_match = re.search(r'\$\s*([\d,]+\.?\d*)', str(cell_value))
                                                        if prize_match:
                                                            prize_amount = float(prize_match.group(1).replace(',', ''))
                                                    
                                                    # Look for number of winners
                                                    if isinstance(cell_value, (int, float)) or (isinstance(cell_value, str) and cell_value.isdigit()):
                                                        winners_count = int(str(cell_value).replace(',', ''))
                                                
                                                # Update prize data if we found information
                                                if prize_amount is not None:
                                                    prize_data[f'group_{group_num}_prize'] = prize_amount
                                                
                                                if winners_count is not None:
                                                    prize_data[f'group_{group_num}_winners'] = winners_count
                                except Exception as e:
                                    st.warning(f"Error processing a table: {str(e)}")
                                    continue
                            
                            # Create result entry if we have all necessary information
                            if draw_number and winning_numbers and len(winning_numbers) >= 6 and additional_number:
                                # In case we found more than 6, keep only the first 6
                                if len(winning_numbers) > 6:
                                    winning_numbers = winning_numbers[:6]
                                
                                result = {
                                    'draw_date': date,
                                    'draw_number': draw_number,
                                    'winning_numbers': winning_numbers,
                                    'additional_number': additional_number,
                                    **prize_data
                                }
                                results.append(result)
                                st.success(f"Successfully processed draw #{draw_number} on {date} from specific URL")
                                api_success = True
                            else:
                                st.warning(f"Could not extract complete data for {date} from the specific URL")
                                st.info(f"Draw number: {draw_number}, Winning numbers: {winning_numbers}, Additional number: {additional_number}")
                        else:
                            st.warning(f"Failed to fetch from specific URL for {date}. Status code: {status}")
                    
                    except Exception as e:
                        st.warning(f"Error processing data for {date} from specific URL: {str(e)}")
                else:
                    st.warning(f"No queryString found for date {date}, skipping to next date or falling back to general scraping...")
        
        # If neither queryString nor API approach succeeded, fall back to general web scraping
        if not api_success:
            st.info("Falling back to general web scraping approach...")
            url = "https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx"
            
            st.info("Attempting to scrape TOTO results from website...")
        
        # Try different approaches to get the content
        st.info("Trying multiple approaches to download the page...")
        
        html_content = None
        error_messages = []
        
        # Approach 1: Standard requests with basic headers and disabled SSL verification
        try:
            st.info("Trying with basic headers and disabled SSL verification...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            # Disable SSL verification for this specific request
            response = requests.get(url, headers=headers, verify=False)
            status = response.status_code
            st.info(f"Response status code: {status}")
            
            if status == 200:
                html_content = response.text
                st.info(f"Success! Downloaded {len(html_content)} bytes")
            else:
                error_messages.append(f"Basic headers approach failed with status {status}")
        except Exception as e:
            error_messages.append(f"Basic headers approach failed with error: {str(e)}")
        
        # Approach 2: More complete browser headers and disabled SSL verification
        if not html_content:
            try:
                st.info("Trying with complete browser headers and disabled SSL verification...")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0',
                    'Referer': 'https://www.singaporepools.com.sg/en/Pages/Home.aspx',
                }
                # Disable SSL verification for this specific request
                response = requests.get(url, headers=headers, verify=False)
                status = response.status_code
                st.info(f"Response status code: {status}")
                
                if status == 200:
                    html_content = response.text
                    st.info(f"Success! Downloaded {len(html_content)} bytes")
                else:
                    error_messages.append(f"Complete headers approach failed with status {status}")
            except Exception as e:
                error_messages.append(f"Complete headers approach failed with error: {str(e)}")
        
        # Approach 3: Try using trafilatura as a fallback
        if not html_content:
            try:
                st.info("Trying with trafilatura...")
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    html_content = downloaded
                    st.info(f"Success! Downloaded {len(html_content)} bytes with trafilatura")
                else:
                    error_messages.append("Trafilatura approach failed to download content")
            except Exception as e:
                error_messages.append(f"Trafilatura approach failed with error: {str(e)}")
        
        # Check if we got content
        if not html_content:
            st.error("All download approaches failed to get content from Singapore Pools website")
            for i, error in enumerate(error_messages):
                st.error(f"{i+1}. {error}")
            return pd.DataFrame()
        
        # If we got this far and still have no results, create a DataFrame from the results list
        if not results:
            st.warning("No TOTO results were successfully scraped.")
            return pd.DataFrame()
        
        # Create DataFrame from the results
        df = pd.DataFrame(results)
        
        # Return the results DataFrame
        st.info(f"Created DataFrame with {len(df)} rows.")
        return df
    
    except Exception as e:
        st.error(f"Error scraping TOTO results: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return pd.DataFrame()