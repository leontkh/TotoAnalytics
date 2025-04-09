import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import traceback
import time
import sys
import io
from io import StringIO

def debug_scrape():
    """Test the scraping function with detailed logs"""
    print("=" * 50)
    print("Starting debug scrape for Singapore Pools TOTO results")
    print("=" * 50)
    
    url = "https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx"
    
    # 1. Download the page content
    print("\n[1] Downloading page content...")
    
    # Try different approaches to get the content
    print("Trying multiple approaches to download the page...")
    
    html_content = None
    error_messages = []
    
    # Approach 1: Standard requests with basic headers
    try:
        print("\n[1.1] Approach 1: Basic requests with User-Agent...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        status = response.status_code
        print(f"Response status code: {status}")
        
        if status == 200:
            html_content = response.text
            print(f"Success! Downloaded {len(html_content)} bytes")
        else:
            error_messages.append(f"Approach 1 failed with status {status}")
    except Exception as e:
        error_messages.append(f"Approach 1 failed with error: {str(e)}")
    
    # Approach 2: More complete browser headers
    if not html_content:
        try:
            print("\n[1.2] Approach 2: Complete browser headers...")
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
            response = requests.get(url, headers=headers)
            status = response.status_code
            print(f"Response status code: {status}")
            
            if status == 200:
                html_content = response.text
                print(f"Success! Downloaded {len(html_content)} bytes")
            else:
                error_messages.append(f"Approach 2 failed with status {status}")
        except Exception as e:
            error_messages.append(f"Approach 2 failed with error: {str(e)}")
    
    # Approach 3: Try using a session with cookies
    if not html_content:
        try:
            print("\n[1.3] Approach 3: Using session with cookies...")
            session = requests.Session()
            
            # First visit the homepage to get cookies
            home_url = "https://www.singaporepools.com.sg/en/Pages/Home.aspx"
            print(f"First visiting homepage at {home_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            home_response = session.get(home_url, headers=headers)
            print(f"Homepage response: {home_response.status_code}")
            
            if home_response.status_code == 200:
                # Now try to access the TOTO results with the session cookies
                print("Now trying TOTO results page with session cookies")
                time.sleep(2)  # Add small delay to be respectful
                
                toto_response = session.get(url, headers=headers)
                status = toto_response.status_code
                print(f"TOTO page response: {status}")
                
                if status == 200:
                    html_content = toto_response.text
                    print(f"Success! Downloaded {len(html_content)} bytes")
                else:
                    error_messages.append(f"Approach 3 failed with status {status}")
            else:
                error_messages.append(f"Approach 3 failed - couldn't access homepage, status {home_response.status_code}")
        except Exception as e:
            error_messages.append(f"Approach 3 failed with error: {str(e)}")
    
    # Check if we got content
    if html_content:
        print("\nSuccessfully downloaded page content!")
        
        # Save first 5000 bytes for inspection
        with open("debug_page_content.html", "w") as f:
            f.write(html_content[:5000])
        print("Saved first 5000 bytes to debug_page_content.html")
    else:
        print("\nERROR: All download approaches failed:")
        for i, error in enumerate(error_messages):
            print(f"  {i+1}. {error}")
        return
    
    # 2. Parse with BeautifulSoup
    print("\n[2] Parsing with BeautifulSoup...")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 3. Extract information
    print("\n[3] Trying to extract TOTO information...")
    
    # 3.1 Find draw date
    print("\n[3.1] Looking for draw date...")
    date_pattern = re.compile(r'\d{1,2}\s+[A-Za-z]+\s+\d{4}')
    date_elements = soup.find_all(string=date_pattern)
    
    if date_elements:
        print(f"Found {len(date_elements)} elements containing date patterns")
        for i, element in enumerate(date_elements[:3]):  # Show first 3
            print(f"Date element {i+1}: {element.strip()[:100]}...")
            
        # Try to extract a date from a non-script element
        draw_date = None
        for element in date_elements:
            if 'CDATA' not in str(element):  # Skip script elements
                draw_date_str = re.search(date_pattern, element).group(0)
                print(f"Potential draw date found: {draw_date_str}")
                try:
                    draw_date = datetime.strptime(draw_date_str, '%d %B %Y').strftime('%Y-%m-%d')
                    print(f"Successfully parsed date: {draw_date}")
                    break
                except ValueError:
                    try:
                        draw_date = datetime.strptime(draw_date_str, '%d %b %Y').strftime('%Y-%m-%d')
                        print(f"Successfully parsed date: {draw_date}")
                        break
                    except ValueError:
                        print(f"Could not parse date format: {draw_date_str}")
    else:
        print("No elements found containing date patterns")
    
    # 3.2 Find draw number
    print("\n[3.2] Looking for draw number...")
    draw_pattern = re.compile(r'Draw No\.?\s*(\d+)', re.IGNORECASE)
    draw_elements = soup.find_all(string=lambda text: bool(text and draw_pattern.search(str(text))))
    
    draw_number = None
    if draw_elements:
        print(f"Found {len(draw_elements)} elements containing draw number patterns")
        for i, element in enumerate(draw_elements[:3]):  # Show first 3
            print(f"Draw element {i+1}: {element.strip()[:100]}...")
            
        for element in draw_elements:
            match = draw_pattern.search(str(element))
            if match:
                draw_number = match.group(1)
                print(f"Extracted draw number: {draw_number}")
                break
    else:
        print("No elements found containing draw number patterns")
    
    # 3.3 Find tables
    print("\n[3.3] Looking for tables...")
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables")
    
    for i, table in enumerate(tables[:3]):  # Show first 3 tables
        print(f"\nTable {i+1}:")
        # Extract table headers
        headers = [th.text.strip() for th in table.find_all('th')]
        print(f"Headers: {headers}")
        
        # Extract first row of data if available
        rows = table.find_all('tr')
        if len(rows) > 1:
            data_cells = rows[1].find_all(['td', 'th'])
            row_data = [cell.text.strip() for cell in data_cells]
            print(f"First row data: {row_data}")
            
            # Try to parse with pandas
            try:
                df_table = pd.read_html(StringIO(str(table)))[0]
                print(f"Parsed table shape: {df_table.shape}")
                print("First few rows:")
                print(df_table.head(2))
            except Exception as e:
                print(f"Failed to parse table with pandas: {str(e)}")
    
    # 3.4 Find winning numbers
    print("\n[3.4] Looking for winning numbers...")
    winning_numbers_header = soup.find(string=re.compile("Winning Numbers", re.IGNORECASE))
    
    if winning_numbers_header:
        print(f"Found 'Winning Numbers' header: {winning_numbers_header.strip()}")
        
        # Look for parent table
        parent = winning_numbers_header.parent
        while parent and parent.name != 'table':
            parent = parent.find_next('table')
        
        if parent and parent.name == 'table':
            print("Found table containing winning numbers")
            number_cells = []
            for cell in parent.find_all(['td', 'th']):
                cell_text = cell.get_text(strip=True)
                if cell_text.isdigit() and 1 <= int(cell_text) <= 49:  # TOTO numbers are 1-49
                    number_cells.append(int(cell_text))
            
            if number_cells:
                print(f"Extracted potential winning numbers: {number_cells}")
            else:
                print("No numbers found in the winning numbers table")
        else:
            print("Could not find table containing winning numbers")
    else:
        print("Could not find 'Winning Numbers' header")
    
    # 3.5 Find additional number
    print("\n[3.5] Looking for additional number...")
    additional_header = soup.find(string=re.compile("Additional Number", re.IGNORECASE))
    
    if additional_header:
        print(f"Found 'Additional Number' header: {additional_header.strip()}")
        
        # Look for parent table
        parent = additional_header.parent
        while parent and parent.name != 'table':
            parent = parent.find_next('table')
        
        if parent and parent.name == 'table':
            print("Found table containing additional number")
            for cell in parent.find_all(['td', 'th']):
                cell_text = cell.get_text(strip=True)
                if cell_text.isdigit() and 1 <= int(cell_text) <= 49:
                    print(f"Extracted potential additional number: {cell_text}")
                    break
        else:
            print("Could not find table containing additional number")
    else:
        print("Could not find 'Additional Number' header")
    
    # 3.6 Check for potential JS-loaded content 
    print("\n[3.6] Checking for JavaScript-loaded content...")
    scripts = soup.find_all('script')
    
    js_urls = []
    for script in scripts:
        if script.get('src'):
            js_urls.append(script.get('src'))
    
    print(f"Found {len(scripts)} script tags, {len(js_urls)} with src attribute")
    
    toto_js = [s for s in scripts if s.string and 'TOTO' in str(s.string)]
    print(f"Found {len(toto_js)} scripts containing 'TOTO'")
    
    # 4. Summary
    print("\n[4] Summary:")
    if draw_date and draw_number:
        print(f"Draw Date: {draw_date}")
        print(f"Draw Number: {draw_number}")
        print("Basic information was found successfully")
    else:
        print("Failed to extract basic draw information")
        if not draw_date:
            print("- Missing draw date")
        if not draw_number:
            print("- Missing draw number")
    
    print("\nDebugging complete\n")

if __name__ == "__main__":
    debug_scrape()