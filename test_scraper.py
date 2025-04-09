import trafilatura
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import json

def test_scrape():
    """Test the scraping function directly"""
    url = "https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx"
    
    print("Testing web scraping...")
    
    # Step 1: Try using trafilatura to get content
    print("Trying with trafilatura...")
    downloaded = trafilatura.fetch_url(url)
    
    if not downloaded:
        print("Failed to download with trafilatura, trying requests...")
        # Fallback to regular requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed with status code: {response.status_code}")
            return
        html_content = response.text
        print(f"Got {len(html_content)} characters with requests")
    else:
        html_content = downloaded
        print(f"Got {len(html_content)} characters with trafilatura")
    
    # Save a small sample of the HTML for inspection
    with open("sample_html.txt", "w") as f:
        f.write(html_content[:5000])
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for TOTO related content
    toto_elements = soup.find_all(string=re.compile("TOTO", re.IGNORECASE))
    print(f"Found {len(toto_elements)} elements containing 'TOTO'")
    
    for i, el in enumerate(toto_elements[:5]):  # Show first 5
        print(f"Element {i+1}: {el.strip()[:100]}...")
    
    # Look for date patterns
    date_pattern = re.compile(r'\d{1,2}\s+[A-Za-z]+\s+\d{4}')
    date_elements = soup.find_all(string=date_pattern)
    print(f"Found {len(date_elements)} elements containing dates")
    
    for i, el in enumerate(date_elements[:5]):  # Show first 5
        print(f"Date {i+1}: {el.strip()[:100]}...")
    
    # Try to find tables 
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables")
    
    # Look for draw number elements
    draw_pattern = re.compile(r'DRAW\s+NO', re.IGNORECASE)
    draw_elements = soup.find_all(string=draw_pattern)
    print(f"Found {len(draw_elements)} elements with draw numbers:")
    for i, el in enumerate(draw_elements[:3]):
        print(f"Draw element {i+1}: {el.strip()[:100]}...")
        
        # Look at parents of these elements to find result blocks
        parent = el.parent
        if parent:
            print(f"Parent of draw element {i+1}: {parent.name} with classes: {parent.get('class', 'No classes')}")
            
            # Look at grandparent to possibly find the actual result block
            grandparent = parent.parent
            if grandparent:
                print(f"Grandparent: {grandparent.name} with classes: {grandparent.get('class', 'No classes')}")
                
                # Look for table in siblings or children of this block
                tables_in_block = grandparent.find_all('table')
                print(f"Found {len(tables_in_block)} tables in this potential result block")
                
                # Look for winning numbers in this block
                numbers = []
                for span in grandparent.find_all(['span', 'div']):
                    if span.string and span.string.strip().isdigit():
                        numbers.append(span.string.strip())
                print(f"Found {len(numbers)} potential winning numbers: {numbers[:10]}")
    
    # Look for specific content in page that might indicate we're getting the right page
    results_section = soup.find(id="ResultsListing")
    if results_section:
        print("Found ResultsListing section")
    else:
        print("Could not find ResultsListing section")
        
    latest_results = soup.find(id="latestResults")
    if latest_results:
        print("Found latestResults section")
    else:
        print("Could not find latestResults section")
    
    # Look for JavaScript variables that might contain the data
    scripts = soup.find_all('script')
    for i, script in enumerate(scripts):
        if script.string and 'TOTO' in script.string:
            print(f"Found script {i+1} with TOTO data:")
            # Look for JSON-like data in script
            json_pattern = re.compile(r'\{.*\:\s*\{.*\}.*\}', re.DOTALL)
            for match in json_pattern.findall(script.string or ""):
                if len(match) < 500:  # Only show reasonably sized matches
                    print(f"Potential JSON data: {match}")
    
    # Try a different API approach - sometimes websites use APIs to load data
    # Check if there are any fetch or XMLHttpRequest calls in the scripts
    api_pattern = re.compile(r'(fetch|XMLHttpRequest|ajax).*?["\'](.*?)["\']', re.DOTALL)
    api_endpoints = []
    for script in scripts:
        if script.string:
            for match in api_pattern.findall(script.string):
                if "toto" in match[1].lower() or "result" in match[1].lower():
                    api_endpoints.append(match[1])
                    
    if api_endpoints:
        print("Found potential API endpoints:")
        for endpoint in api_endpoints:
            print(f"- {endpoint}")
    else:
        print("No potential API endpoints found")
    
    # Check for iframes that might contain the results
    iframes = soup.find_all('iframe')
    if iframes:
        print(f"Found {len(iframes)} iframes, which might contain the results:")
        for i, iframe in enumerate(iframes):
            print(f"iframe {i+1} src: {iframe.get('src', 'No src')}")
    
    # Check for any structured data
    try:
        for script in soup.find_all('script', {'type': 'application/ld+json'}):
            data = json.loads(script.string)
            print(f"Found structured data: {json.dumps(data, indent=2)[:200]}...")
    except:
        print("No valid structured data found")

if __name__ == "__main__":
    test_scrape()