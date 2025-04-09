import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import re
import trafilatura
import io
from io import StringIO

def find_query_str():
    """
    Fetch and extract TOTO result query strings and corresponding dates from Singapore Pools website
    
    Returns:
        A list of dictionaries, each containing:
        - query_string: The query string to use with scrape_toto_results
        - draw_date: The date of the draw in YYYY-MM-DD format
        - draw_number: The draw number (if available)
    """
    url = "https://www.singaporepools.com.sg/DataFileArchive/Lottery/Output/toto_result_draw_list_en.html"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.singaporepools.com.sg/en/Pages/Home.aspx',
    }

    print("Fetching TOTO result query strings...")
    
    # Disable SSL verification
    response = requests.get(url, headers=headers, verify=False)
    
    if response.status_code != 200:
        print(f"Failed to fetch query strings (HTTP {response.status_code})")
        return []
    
    # Parse the HTML content
    content = response.text
    soup = BeautifulSoup(content, 'html.parser')
    
    # Find all options in the HTML that contain query strings
    draw_info_list = []
    
    # Look for select elements that might contain the draw options
    select_elements = soup.find_all('select')
    
    for select in select_elements:
        options = select.find_all('option')
        
        for option in options:
            if 'queryString' in str(option):
                # Extract the query string using regex
                query_match = re.search(r"queryString='([^']+)'", str(option))
                
                if query_match:
                    query_string = query_match.group(1)
                    
                    # Extract the draw date and number from the option text
                    option_text = option.get_text(strip=True)
                    
                    # Try to extract date and draw number from option text
                    date_match = re.search(r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})', option_text)
                    draw_match = re.search(r'Draw\s*(?:No\.?)?:?\s*#?(\d+)', option_text, re.IGNORECASE)
                    
                    draw_date = None
                    draw_number = None
                    
                    # Parse the date if found
                    if date_match:
                        date_str = date_match.group(1)
                        try:
                            # Try different date formats
                            date_formats = ['%d %B %Y', '%d %b %Y']
                            for fmt in date_formats:
                                try:
                                    draw_date = datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
                                    break
                                except ValueError:
                                    continue
                        except Exception as e:
                            print(f"Error parsing date {date_str}: {str(e)}")
                    
                    # Parse the draw number if found
                    if draw_match:
                        draw_number = draw_match.group(1)
                        try:
                            draw_number = int(draw_number)
                        except ValueError:
                            print(f"Error parsing draw number {draw_number}")
                    
                    # Extract draw ID from query string as fallback for draw number
                    if draw_number is None and 'id=' in query_string:
                        try:
                            draw_id = query_string.split('id=')[1].split('&')[0]
                            if draw_id.isdigit():
                                draw_number = int(draw_id)
                        except Exception:
                            pass
                    
                    # Add the info to our list
                    draw_info = {
                        'query_string': query_string,
                        'draw_date': draw_date,
                        'draw_number': draw_number
                    }
                    
                    draw_info_list.append(draw_info)
    
    if not draw_info_list:
        # Fallback to just extracting query strings if the above method fails
        print("Couldn't find draw info using the HTML parser, falling back to regex-only approach")
        pattern = r"queryString='([^']+)' value='([^']+)'"
        matches = re.findall(pattern, content)
        
        for match in matches:
            query_string = match[0]
            option_text = match[1]
            
            # Try to extract date and draw number from option text
            date_match = re.search(r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})', option_text)
            draw_match = re.search(r'Draw\s*(?:No\.?)?:?\s*#?(\d+)', option_text, re.IGNORECASE)
            
            draw_date = None
            draw_number = None
            
            if date_match:
                date_str = date_match.group(1)
                try:
                    # Try different date formats
                    date_formats = ['%d %B %Y', '%d %b %Y']
                    for fmt in date_formats:
                        try:
                            draw_date = datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
            
            if draw_match:
                draw_number = draw_match.group(1)
                try:
                    draw_number = int(draw_number)
                except ValueError:
                    pass
            
            # Extract draw ID from query string as fallback for draw number
            if draw_number is None and 'id=' in query_string:
                try:
                    draw_id = query_string.split('id=')[1].split('&')[0]
                    if draw_id.isdigit():
                        draw_number = int(draw_id)
                except Exception:
                    pass
            
            draw_info = {
                'query_string': query_string,
                'draw_date': draw_date,
                'draw_number': draw_number
            }
            
            draw_info_list.append(draw_info)
    
    # If all else fails, just return query strings without dates (original functionality)
    if not draw_info_list:
        print("Falling back to original regex approach (query strings only)")
        pattern = r"queryString='(.{4}=.{20})' value='"
        query_strings = re.findall(pattern, content)
        draw_info_list = [{'query_string': q, 'draw_date': None, 'draw_number': None} for q in query_strings]
    
    print(f"Found {len(draw_info_list)} query strings with draw information")
    return draw_info_list

def scrape_toto_results(query_str=None):
    """
    Scrape TOTO results from Singapore Pools website

    Args:
        dates_to_scrape: List of dates to scrape. If None, scrape the latest result.

    Returns:
        A DataFrame containing the scraped TOTO results
    """
    url = "https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx"
    if query_str is not None:
        url = url + "?" + query_str
    results = []

    try:
        print("Attempting to scrape TOTO results...")

        # Use a modern browser user agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            # First download with requests
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            html_content = response.text
            print(f"Downloaded {len(html_content)} bytes with requests")
        except Exception as e:
            print(f"Error downloading with requests: {str(e)}")
            # Try trafilatura as fallback
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                print("Failed to download the page content.")
                return pd.DataFrame()
            html_content = downloaded
            print(f"Downloaded {len(html_content)} bytes with trafilatura")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Try to extract tables directly
        all_tables = soup.find_all('table')
        print(f"Found {len(all_tables)} tables on the page")

        # First try to find draw date and number
        draw_info = {}

        # Look for draw date in the page
        date_pattern = re.compile(r'\d{1,2}\s+[A-Za-z]+\s+\d{4}')
        date_elements = soup.find_all(string=date_pattern)

        if date_elements:
            for element in date_elements:
                if 'CDATA' not in element:  # Skip script elements
                    draw_date_str = re.search(date_pattern, element).group(0)
                    try:
                        draw_date = datetime.strptime(draw_date_str, '%d %B %Y').strftime('%Y-%m-%d')
                        draw_info['draw_date'] = draw_date
                        print(f"Found draw date: {draw_date}")
                        break
                    except ValueError:
                        try:
                            draw_date = datetime.strptime(draw_date_str, '%d %b %Y').strftime('%Y-%m-%d')
                            draw_info['draw_date'] = draw_date
                            print(f"Found draw date: {draw_date}")
                            break
                        except ValueError:
                            pass

        # Look for draw number
        draw_pattern = re.compile(r'Draw No\.?\s*(\d+)', re.IGNORECASE)
        draw_elements = soup.find_all(string=lambda text: bool(text and draw_pattern.search(text)))

        if draw_elements:
            for element in draw_elements:
                match = draw_pattern.search(element)
                if match:
                    draw_number = match.group(1)
                    draw_info['draw_number'] = int(draw_number)
                    print(f"Found draw number: {draw_number}")
                    break

        # If we don't have both draw date and number, can't proceed
        if 'draw_date' not in draw_info or 'draw_number' not in draw_info:
            print("Could not find draw date or number")
            return pd.DataFrame()

        # Extract winning numbers
        winning_numbers = []
        additional_number = None

        # Look for the table that contains the winning numbers
        winning_numbers_header = soup.find(string=re.compile("Winning Numbers", re.IGNORECASE))
        if winning_numbers_header:
            # Find the table near this header
            parent = winning_numbers_header.parent
            while parent and parent.name != 'table':
                parent = parent.parent

            if parent and parent.name == 'table':
                # Extract numbers from this table
                for cell in parent.find_all(['td', 'th']):
                    cell_text = cell.get_text(strip=True)
                    if cell_text.isdigit() and 1 <= int(cell_text) <= 49:  # TOTO numbers are 1-49
                        winning_numbers.append(int(cell_text))

        # Look for additional number
        additional_header = soup.find(string=re.compile("Additional Number", re.IGNORECASE))
        if additional_header:
            # Find closest table
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

            print(f"Found winning numbers: {winning_numbers}")
            print(f"Found additional number: {additional_number}")
        else:
            print("Could not find the complete set of winning numbers")
            if winning_numbers:
                print(f"Partial winning numbers found: {winning_numbers}")
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
                    print("Found prize table")

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
                print(f"Error processing a table: {str(e)}")
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
        print(f"Successfully processed draw #{draw_info['draw_number']} on {draw_info['draw_date']}")

        # Create DataFrame from results
        df = pd.DataFrame(results)

        if df.empty:
            print("No TOTO results found on the page.")
        else:
            print(f"Successfully scraped {len(df)} TOTO results.")

        return df

    except Exception as e:
        print(f"Error scraping TOTO results: {str(e)}")
        return pd.DataFrame()
