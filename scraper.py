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
    url = "https://www.singaporepools.com.sg/DataFileArchive/Lottery/Output/toto_result_draw_list_en.html"
    
    st.info("Fetching available draw dates from Singapore Pools API...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.singaporepools.com.sg/en/Pages/Home.aspx',
    }
    
    try:
        # Disable SSL verification
        response = requests.get(url, headers=headers, verify=False)
        
        if response.status_code == 200:
            try:
                # Try to parse as JSON
                data = response.json()
                st.info("Successfully fetched draw dates as JSON")
                
                # Extract draw dates and queryStrings from the JSON data
                date_to_query = {}
                
                # Check the structure of the JSON data
                if isinstance(data, list):
                    # If it's a list of draw information
                    for draw in data:
                        if 'drawDate' in draw and 'queryString' in draw:
                            date_str = draw['drawDate']
                            query_string = draw['queryString']
                            
                            try:
                                # Try to parse the date based on the format returned by the API
                                # The API might return dates in different formats, so we try a few common ones
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
                                    st.info(f"Found draw date: {date_formatted} with query string: {query_string}")
                            except Exception as e:
                                st.warning(f"Failed to parse date {date_str}: {str(e)}")
                
                # Sort dates in descending order (most recent first)
                sorted_dates = sorted(date_to_query.keys(), reverse=True)
                sorted_date_to_query = {date: date_to_query[date] for date in sorted_dates}
                
                # Log the number of available dates
                st.info(f"Found {len(sorted_date_to_query)} available draw dates")
                return sorted_date_to_query
            
            except json.JSONDecodeError:
                # If it's not valid JSON, try to parse as HTML
                st.info("Response is not JSON, trying to parse as HTML...")
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for draw elements in the HTML
                date_to_query = {}
                
                # Detailed log of HTML content for debugging
                st.write("HTML content snippet:")
                st.code(soup.prettify()[:1000])  # Display the first 1000 characters of the HTML
                
                # Find select dropdown with draw dates (typically has class 'selectDrawList')
                select_element = soup.find('select', class_='selectDrawList')
                st.write(f"Select element found: {select_element is not None}")
                
                if select_element:
                    st.info("Found draw list dropdown")
                    # Log the dropdown HTML
                    st.code(select_element.prettify())
                    
                    # Extract options from the select element
                    options = select_element.find_all('option')
                    st.write(f"Number of options found: {len(options)}")
                    
                    for i, option in enumerate(options):
                        st.write(f"Processing option {i+1}:")
                        st.write(f"Option attributes: {option.attrs}")
                        st.write(f"Option text: {option.get_text(strip=True)}")
                        
                        if 'queryString' in option.attrs:
                            query_string = option['queryString']
                            option_text = option.get_text(strip=True)
                            
                            # Extract date from the option text (typically in format like "Mon, 07 Apr 2025")
                            try:
                                # Try to parse date with various formats
                                date_formatted = None
                                for fmt in ['%a, %d %b %Y', '%d %b %Y', '%d/%m/%Y', '%Y-%m-%d']:
                                    try:
                                        date = datetime.strptime(option_text, fmt)
                                        date_formatted = date.strftime('%Y-%m-%d')
                                        st.success(f"Successfully parsed date {option_text} with format {fmt}")
                                        break
                                    except ValueError:
                                        st.write(f"Failed to parse with format {fmt}")
                                        continue
                                
                                if date_formatted:
                                    date_to_query[date_formatted] = query_string
                                    st.success(f"Found draw date: {date_formatted} with query string: {query_string}")
                                else:
                                    st.warning(f"Could not parse date from option text: {option_text}")
                            except Exception as e:
                                st.warning(f"Failed to parse date from option: {option_text}, error: {str(e)}")
                
                # If no select dropdown found, try alternative method with links
                if not date_to_query:
                    st.info("No dropdown found, trying alternative method with links...")
                    # Look for elements with href attributes
                    for link in soup.find_all('a', href=True):
                        href = link.get('href')
                        # Check if this link might be to a draw result page
                        if 'toto_results.aspx?' in href:
                            # Extract the query string
                            query_string = href.split('toto_results.aspx?')[1]
                            # Try to find a date in the link text
                            link_text = link.get_text(strip=True)
                            date_pattern = re.compile(r'\d{1,2}[/\-\s][A-Za-z]{0,9}[/\-\s]\d{4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2}')
                            date_match = date_pattern.search(link_text)
                            
                            if date_match:
                                date_str = date_match.group(0)
                                try:
                                    # Try various date formats
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
                                        st.info(f"Found draw date: {date_formatted} with query string: {query_string}")
                                except Exception as e:
                                    st.warning(f"Failed to parse date {date_str}: {str(e)}")
                
                # Sort dates in descending order (most recent first)
                sorted_dates = sorted(date_to_query.keys(), reverse=True)
                sorted_date_to_query = {date: date_to_query[date] for date in sorted_dates}
                
                # Log the number of available dates
                st.info(f"Found {len(sorted_date_to_query)} available draw dates from HTML")
                return sorted_date_to_query
        
        else:
            st.error(f"Failed to fetch draw dates. Status code: {response.status_code}")
            return {}
    
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
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Try to extract tables directly
        all_tables = soup.find_all('table')
        st.info(f"Found {len(all_tables)} tables on the page")
        
        # First try to find draw date and number
        draw_info = {}
        
        # Look for draw date in the page
        date_pattern = re.compile(r'\d{1,2}\s+[A-Za-z]+\s+\d{4}')
        date_elements = soup.find_all(string=lambda text: bool(text and date_pattern.search(str(text))))
        
        if date_elements:
            for element in date_elements:
                element_str = str(element)
                if 'CDATA' not in element_str:  # Skip script elements
                    draw_date_str = re.search(date_pattern, element_str).group(0)
                    try:
                        draw_date = datetime.strptime(draw_date_str, '%d %B %Y').strftime('%Y-%m-%d')
                        draw_info['draw_date'] = draw_date
                        st.info(f"Found draw date: {draw_date}")
                        break
                    except ValueError:
                        try:
                            draw_date = datetime.strptime(draw_date_str, '%d %b %Y').strftime('%Y-%m-%d')
                            draw_info['draw_date'] = draw_date
                            st.info(f"Found draw date: {draw_date}")
                            break
                        except ValueError:
                            pass
        
        # Look for draw number
        draw_pattern = re.compile(r'Draw No\.?\s*(\d+)', re.IGNORECASE)
        draw_elements = soup.find_all(string=lambda text: bool(text and draw_pattern.search(str(text))))
        
        if draw_elements:
            for element in draw_elements:
                element_str = str(element)
                match = draw_pattern.search(element_str)
                if match:
                    draw_number = match.group(1)
                    draw_info['draw_number'] = int(draw_number)
                    st.info(f"Found draw number: {draw_number}")
                    break
        
        # If we don't have both draw date and number, can't proceed
        if 'draw_date' not in draw_info or 'draw_number' not in draw_info:
            st.error("Could not find draw date or number")
            return pd.DataFrame()
        
        # Extract winning numbers
        winning_numbers = []
        additional_number = None
        
        # Look for the table that contains the winning numbers
        winning_numbers_header = soup.find(string=re.compile("Winning Numbers", re.IGNORECASE))
        if winning_numbers_header:
            # Find the table by going up the DOM tree
            parent = winning_numbers_header.parent
            while parent and parent.name != 'table':
                parent = parent.parent
            
            if parent and parent.name == 'table':
                # Extract numbers from this table
                for cell in parent.find_all(['td', 'th']):
                    cell_text = cell.get_text(strip=True)
                    if cell_text.isdigit() and 1 <= int(cell_text) <= 49:  # TOTO numbers are 1-49
                        winning_numbers.append(int(cell_text))
        
        # If still no winning numbers, try to find them by looking at all tables
        if not winning_numbers:
            for table in all_tables:
                # Look for a table with digits 1-49 in its cells
                potential_numbers = []
                for cell in table.find_all(['td', 'th']):
                    cell_text = cell.get_text(strip=True)
                    if cell_text.isdigit() and 1 <= int(cell_text) <= 49:
                        potential_numbers.append(int(cell_text))
                
                # If we found a table with 6 or 7 numbers, that's likely our winning numbers
                if 6 <= len(potential_numbers) <= 7:
                    winning_numbers = potential_numbers[:6]
                    if len(potential_numbers) == 7:
                        additional_number = potential_numbers[6]
                    break
        
        # Look for additional number
        if additional_number is None:
            additional_header = soup.find(string=re.compile("Additional Number", re.IGNORECASE))
            if additional_header:
                # Find closest table by going up the DOM tree
                parent = additional_header.parent
                while parent and parent.name != 'table':
                    parent = parent.parent
                
                if parent and parent.name == 'table':
                    for cell in parent.find_all(['td', 'th']):
                        cell_text = cell.get_text(strip=True)
                        if cell_text.isdigit() and 1 <= int(cell_text) <= 49:
                            additional_number = int(cell_text)
                            break
        
        # If we didn't find winning numbers through tables, try an alternative approach
        # Look for numbers in the sequence of cells that could be winning numbers
        if not winning_numbers:
            for div in soup.find_all(['div', 'span']):
                text = div.get_text(strip=True)
                if text.isdigit() and 1 <= int(text) <= 49:
                    winning_numbers.append(int(text))
                    # If we have 6 numbers, the next one might be the additional
                    if len(winning_numbers) == 6 and additional_number is None:
                        # Look at next div/span
                        next_element = div.find_next(['div', 'span'])
                        if next_element:
                            next_text = next_element.get_text(strip=True)
                            if next_text.isdigit() and 1 <= int(next_text) <= 49:
                                additional_number = int(next_text)
                        break
        
        # If we found at least 6 numbers (standard TOTO has 6 winning numbers)
        if len(winning_numbers) >= 6:
            # In case we found more than 6, keep only the first 6
            if len(winning_numbers) > 6 and additional_number is None:
                additional_number = winning_numbers[6]
                winning_numbers = winning_numbers[:6]
            
            st.info(f"Found winning numbers: {winning_numbers}")
            st.info(f"Found additional number: {additional_number}")
        else:
            st.error("Could not find the complete set of winning numbers")
            if winning_numbers:
                st.info(f"Partial winning numbers found: {winning_numbers}")
            return pd.DataFrame()
        
        # Extract prize data using tables
        prize_data = {
            'group_1_winners': 0, 'group_1_prize': 0,
            'group_2_winners': 0, 'group_2_prize': 0,
            'group_3_winners': 0, 'group_3_prize': 0,
            'group_4_winners': 0, 'group_4_prize': 0,
            'group_5_winners': 0, 'group_5_prize': 0,
            'group_6_winners': 0, 'group_6_prize': 0,
            'group_7_winners': 0, 'group_7_prize': 0
        }
        
        # Look for the winning shares table
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
                            
                            # Also try to match "N winners" pattern
                            if winners_count is None:
                                for _, cell_value in row_dict.items():
                                    if isinstance(cell_value, str):
                                        winners_match = re.search(r'(\d+)[^\d]*winners', str(cell_value), re.IGNORECASE)
                                        if winners_match:
                                            winners_count = int(winners_match.group(1).replace(',', ''))
                            
                            # Update prize data if we found information
                            if prize_amount is not None:
                                prize_data[f'group_{group_num}_prize'] = prize_amount
                            
                            if winners_count is not None:
                                prize_data[f'group_{group_num}_winners'] = winners_count
            except Exception as e:
                st.warning(f"Error processing a table: {str(e)}")
                continue
        
        # If we don't have all the data in the prize_data dictionary yet,
        # try to extract directly from the table that has 'Group 1' in it
        if all(value == 0 for key, value in prize_data.items() if key.endswith('_prize')):
            group_1_element = soup.find(string=re.compile(r'Group\s*1', re.IGNORECASE))
            if group_1_element:
                parent_row = group_1_element.find_parent('tr')
                if parent_row:
                    cells = parent_row.find_all(['td', 'th'])
                    for cell in cells:
                        cell_text = cell.get_text(strip=True)
                        if '$' in cell_text:
                            prize_match = re.search(r'\$\s*([\d,]+\.?\d*)', cell_text)
                            if prize_match:
                                prize_data['group_1_prize'] = float(prize_match.group(1).replace(',', ''))
                        elif cell_text.isdigit():
                            prize_data['group_1_winners'] = int(cell_text)
        
        # Create a result entry
        result = {
            'draw_date': draw_info['draw_date'],
            'draw_number': draw_info['draw_number'],
            'winning_numbers': winning_numbers,
            'additional_number': additional_number,
            **prize_data
        }
        
        results.append(result)
        st.success(f"Successfully processed draw #{draw_info['draw_number']} on {draw_info['draw_date']}")
        
        # Create DataFrame from results
        df = pd.DataFrame(results)
        
        if df.empty:
            st.warning("No TOTO results found on the page.")
        else:
            st.success(f"Successfully scraped {len(df)} TOTO results.")
        
        return df
    
    except Exception as e:
        st.error(f"Error scraping TOTO results: {str(e)}")
        return pd.DataFrame()
