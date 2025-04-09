import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st

def fetch_toto_data():
    """
    Try to fetch TOTO data from the Singapore Pools API or mobile API endpoints
    """
    # Singapore Pools seems to be using a REST API for their mobile app
    # or to populate their website dynamically
    
    # Different API endpoints to try
    endpoints = [
        "https://www.singaporepools.com.sg/_layouts/15/SPPL/api/lottery/results",
        "https://www.singaporepools.com.sg/api/services/toto/results",
        "https://www.singaporepools.com.sg/en/api/services/toto/results"
    ]
    
    today = datetime.now()
    one_month_ago = today - timedelta(days=30)
    today_str = today.strftime("%Y-%m-%d")
    one_month_ago_str = one_month_ago.strftime("%Y-%m-%d")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx'
    }
    
    params = {
        'gameType': 'TOTO',
        'startDate': one_month_ago_str,
        'endDate': today_str,
        'sort': 'desc'
    }
    
    # Try each endpoint
    for endpoint in endpoints:
        try:
            print(f"Trying endpoint: {endpoint}")
            response = requests.get(endpoint, headers=headers, params=params)
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print("JSON response received:")
                    print(json.dumps(data, indent=2)[:500])  # Print first 500 chars
                    return data
                except:
                    print("Failed to parse JSON response")
                    print(response.text[:200])  # Print first 200 chars of response
        except Exception as e:
            print(f"Error with endpoint {endpoint}: {str(e)}")
    
    return None

if __name__ == "__main__":
    result = fetch_toto_data()
    if result:
        print("Success! Found TOTO data via API.")
    else:
        print("Failed to find TOTO data via API endpoints.")