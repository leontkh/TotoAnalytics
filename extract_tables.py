import trafilatura
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import json

def extract_tables():
    """Extract tables from the Singapore Pools website"""
    url = "https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx"
    
    # Use requests with a modern user agent to get content
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed with status code: {response.status_code}")
        return
    
    html_content = response.text
    print(f"Downloaded {len(html_content)} bytes of HTML")
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all tables on the page
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables")
    
    # Examine each table to see if it contains TOTO results
    for i, table in enumerate(tables):
        print(f"\nTable {i+1}:")
        
        # Check if this table looks like a TOTO results table
        headers = [th.text.strip() for th in table.find_all('th')]
        print(f"Headers: {headers}")
        
        # Check table rows
        rows = table.find_all('tr')
        print(f"Number of rows: {len(rows)}")
        
        if len(rows) > 1:  # At least one header row and one data row
            # Get text from first data row to see content
            data_cells = rows[1].find_all(['td', 'th'])
            row_data = [cell.text.strip() for cell in data_cells]
            print(f"First row data: {row_data}")
            
            # Check if this looks like a TOTO results table
            toto_related = any('draw' in h.lower() for h in headers) or \
                          any('group' in h.lower() for h in headers) or \
                          any('prize' in h.lower() for h in headers)
            
            if toto_related:
                print("This appears to be a TOTO-related table!")
                
                # Try to extract a full DataFrame from this table
                try:
                    df = pd.read_html(str(table))[0]
                    print("\nExtracted DataFrame:")
                    print(df.head(2))  # Show first two rows
                    
                    # Save to CSV for inspection
                    csv_filename = f"table_{i+1}.csv"
                    df.to_csv(csv_filename, index=False)
                    print(f"Saved to {csv_filename}")
                except Exception as e:
                    print(f"Failed to extract DataFrame: {e}")
            else:
                print("Not a TOTO results table")
    
    # Look for any pre-rendered JSON data that might contain results
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and ('TOTO' in script.string or 'toto' in script.string or 'result' in script.string):
            # Look for JSON objects in script
            json_pattern = re.compile(r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}')
            potential_json = json_pattern.findall(script.string or "")
            
            for json_str in potential_json:
                if len(json_str) > 50 and len(json_str) < 1000:  # Avoid tiny or huge matches
                    try:
                        data = json.loads(json_str)
                        # Check if it contains TOTO related data
                        if any(key in str(data).lower() for key in ['toto', 'draw', 'winning', 'number']):
                            print("\nFound JSON data with TOTO information:")
                            print(json.dumps(data, indent=2)[:500])  # Show first 500 chars
                    except:
                        pass  # Not valid JSON

if __name__ == "__main__":
    extract_tables()