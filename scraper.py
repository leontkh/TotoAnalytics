import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import streamlit as st
import re
import trafilatura

def scrape_toto_results(dates_to_scrape=None):
    """
    Scrape TOTO results from Singapore Pools website
    
    Args:
        dates_to_scrape: List of dates to scrape. If None, scrape the latest result.
    
    Returns:
        A DataFrame containing the scraped TOTO results
    """
    url = "https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx"
    results = []
    
    try:
        st.info("Attempting to scrape TOTO results...")
        
        # Use trafilatura to download the page content - handles modern web page structures better
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            st.error("Failed to download the page content using trafilatura.")
            # Fallback to regular requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            html_content = response.text
        else:
            html_content = downloaded
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for result blocks with different possible class names
        result_blocks = soup.find_all('div', class_=['result-block', 'lottery-result', 'toto-result-block', 'toto-results'])
        
        if not result_blocks:
            st.warning("No result blocks found with expected class names. Trying alternative methods...")
            # Try to find blocks based on content patterns instead of class names
            possible_blocks = soup.find_all('div')
            result_blocks = [div for div in possible_blocks if 
                             div.find(text=re.compile("DRAW NO", re.IGNORECASE)) or 
                             div.find(text=re.compile("TOTO", re.IGNORECASE))]
        
        st.info(f"Found {len(result_blocks)} potential result blocks.")
        
        # Process each block
        for i, block in enumerate(result_blocks):
            try:
                # Try to extract draw information
                # Look for text that contains date patterns and draw numbers
                draw_info_text = None
                draw_info_element = block.find(text=re.compile(r'\d{1,2}\s+[A-Za-z]+\s+\d{4}'))
                
                if draw_info_element:
                    # If we found date text, get the containing element's full text
                    parent = draw_info_element.parent
                    draw_info_text = parent.get_text(strip=True) if parent else draw_info_element
                
                if not draw_info_text:
                    # Try to find any div that might contain the draw info
                    for div in block.find_all('div'):
                        if re.search(r'\d{1,2}\s+[A-Za-z]+\s+\d{4}', div.text) or re.search(r'DRAW\s+NO', div.text, re.IGNORECASE):
                            draw_info_text = div.text.strip()
                            break
                
                if not draw_info_text:
                    st.warning(f"Could not find draw info in block {i+1}. Skipping...")
                    continue
                
                # Extract draw date and number
                draw_date_match = re.search(r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})', draw_info_text)
                draw_number_match = re.search(r'DRAW\s+NO\.?\s*(\d+)', draw_info_text, re.IGNORECASE)
                
                if draw_date_match and draw_number_match:
                    draw_date_str = draw_date_match.group(1)
                    try:
                        draw_date = datetime.strptime(draw_date_str, '%d %B %Y').strftime('%Y-%m-%d')
                    except ValueError:
                        try:
                            draw_date = datetime.strptime(draw_date_str, '%d %b %Y').strftime('%Y-%m-%d')
                        except ValueError:
                            st.warning(f"Couldn't parse date format: {draw_date_str}")
                            continue
                    
                    draw_number = draw_number_match.group(1)
                    st.info(f"Found draw #{draw_number} on {draw_date}")
                else:
                    st.warning(f"Failed to extract date or draw number from: {draw_info_text}")
                    continue
                
                # Extract winning numbers - try different approaches
                winning_numbers = []
                additional_number = None
                
                # Look for winning numbers divs with potential class names
                winning_num_classes = ['win-num', 'winning-number', 'toto-winnums', 'number']
                found_winning_numbers = False
                
                for class_name in winning_num_classes:
                    number_elements = block.find_all('div', class_=class_name)
                    if number_elements and len(number_elements) > 0:
                        # If we have 7 numbers, the last one is likely the additional number
                        if len(number_elements) == 7:
                            winning_numbers = [int(num.text.strip()) for num in number_elements[:6]]
                            additional_number = int(number_elements[6].text.strip())
                        else:
                            winning_numbers = [int(num.text.strip()) for num in number_elements]
                        found_winning_numbers = True
                        break
                
                # If still not found, look for any divs or spans with just numbers
                if not found_winning_numbers:
                    number_pattern = re.compile(r'^\s*\d{1,2}\s*$')
                    number_elements = [el for el in block.find_all(['div', 'span']) 
                                      if el.text.strip() and number_pattern.match(el.text)]
                    
                    if number_elements and 6 <= len(number_elements) <= 7:
                        winning_numbers = [int(num.text.strip()) for num in number_elements[:6]]
                        if len(number_elements) == 7:
                            additional_number = int(number_elements[6].text.strip())
                        found_winning_numbers = True
                
                if not found_winning_numbers or not winning_numbers:
                    st.warning(f"Could not find winning numbers for draw {draw_number}. Skipping...")
                    continue
                
                # Default values for winning shares
                prize_data = {
                    'group_1_winners': 0, 'group_1_prize': 0,
                    'group_2_winners': 0, 'group_2_prize': 0,
                    'group_3_winners': 0, 'group_3_prize': 0,
                    'group_4_winners': 0, 'group_4_prize': 0,
                    'group_5_winners': 0, 'group_5_prize': 0,
                    'group_6_winners': 0, 'group_6_prize': 0,
                    'group_7_winners': 0, 'group_7_prize': 0,
                    'jackpot_amount': None
                }
                
                # Try to find the prize table - look for any table
                tables = block.find_all('table')
                if tables:
                    for table in tables:
                        rows = table.find_all('tr')
                        if not rows or len(rows) < 2:
                            continue
                            
                        # Check first row to see if it looks like a prize table
                        header = rows[0].get_text(strip=True).lower()
                        if any(term in header for term in ['group', 'prize', 'winner']):
                            for row in rows[1:]:  # Skip header
                                cells = row.find_all(['td', 'th'])
                                if len(cells) >= 3:
                                    # Get the text from the first cell to identify the group
                                    group_text = cells[0].get_text(strip=True)
                                    group_match = re.search(r'Group\s*(\d)', group_text, re.IGNORECASE)
                                    
                                    if group_match:
                                        group_num = int(group_match.group(1))
                                        
                                        # Try to extract winners and prize
                                        winners_text = cells[1].get_text(strip=True)
                                        prize_text = cells[2].get_text(strip=True)
                                        
                                        # Extract numbers
                                        winners = 0
                                        if winners_text != '-':
                                            winners_match = re.search(r'(\d+[,\d]*)', winners_text)
                                            if winners_match:
                                                winners = int(winners_match.group(1).replace(',', ''))
                                        
                                        prize = 0
                                        if prize_text != '-':
                                            prize_match = re.search(r'\$\s*(\d+[,.\d]*)', prize_text)
                                            if prize_match:
                                                prize = float(prize_match.group(1).replace(',', ''))
                                        
                                        prize_data[f'group_{group_num}_winners'] = winners
                                        prize_data[f'group_{group_num}_prize'] = prize
                
                # Look for jackpot amount
                jackpot_text = block.find(text=re.compile('jackpot', re.IGNORECASE))
                if jackpot_text:
                    # Search for currency amount in parent element text
                    jackpot_container = jackpot_text.parent
                    if jackpot_container:
                        jackpot_full_text = jackpot_container.get_text(strip=True)
                        jackpot_match = re.search(r'\$\s*(\d+[,.\d]*)', jackpot_full_text)
                        if jackpot_match:
                            prize_data['jackpot_amount'] = float(jackpot_match.group(1).replace(',', ''))
                
                # Only process results for the specified dates if provided
                if dates_to_scrape is None or draw_date in dates_to_scrape:
                    result = {
                        'draw_date': draw_date,
                        'draw_number': int(draw_number),
                        'winning_numbers': winning_numbers,
                        'additional_number': additional_number,
                        **prize_data
                    }
                    results.append(result)
                    
                    st.success(f"Successfully processed draw #{draw_number} on {draw_date}")
            except Exception as e:
                st.error(f"Error processing a result block {i+1}: {str(e)}")
                continue
        
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
