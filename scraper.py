import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import streamlit as st
import re

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
        # Make request to the website
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the results section
        result_blocks = soup.find_all('div', class_='result-block')
        
        # Process each block
        for block in result_blocks:
            try:
                # Extract draw date and number
                draw_info = block.find('div', class_='drawInfo').text.strip()
                draw_date_match = re.search(r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})', draw_info)
                draw_number_match = re.search(r'DRAW\s+NO\.\s+(\d+)', draw_info)
                
                if draw_date_match and draw_number_match:
                    draw_date_str = draw_date_match.group(1)
                    draw_date = datetime.strptime(draw_date_str, '%d %B %Y').strftime('%Y-%m-%d')
                    draw_number = draw_number_match.group(1)
                else:
                    continue
                
                # Extract winning numbers
                winning_numbers_div = block.find('div', class_='toto-winnums')
                if not winning_numbers_div:
                    continue
                    
                winning_numbers = [int(num.text.strip()) for num in winning_numbers_div.find_all('div', class_='win-num')]
                
                # Extract additional number
                additional_number_div = block.find('div', class_='additional-num')
                if additional_number_div:
                    additional_number = int(additional_number_div.find('div', class_='win-num').text.strip())
                else:
                    additional_number = None
                
                # Extract winning shares
                winning_shares_table = block.find('table', class_='table-responsive')
                
                # Default values for winning shares
                group_1_winners = 0
                group_1_prize = 0
                group_2_winners = 0
                group_2_prize = 0
                group_3_winners = 0
                group_3_prize = 0
                group_4_winners = 0
                group_4_prize = 0
                group_5_winners = 0
                group_5_prize = 0
                group_6_winners = 0
                group_6_prize = 0
                group_7_winners = 0
                group_7_prize = 0
                
                if winning_shares_table:
                    rows = winning_shares_table.find_all('tr')
                    for row in rows[1:]:  # Skip header row
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            group = cells[0].text.strip()
                            winners = int(cells[1].text.strip().replace(',', '')) if cells[1].text.strip() != '-' else 0
                            prize = float(cells[2].text.strip().replace('$', '').replace(',', '')) if cells[2].text.strip() != '-' else 0
                            
                            if 'Group 1' in group:
                                group_1_winners = winners
                                group_1_prize = prize
                            elif 'Group 2' in group:
                                group_2_winners = winners
                                group_2_prize = prize
                            elif 'Group 3' in group:
                                group_3_winners = winners
                                group_3_prize = prize
                            elif 'Group 4' in group:
                                group_4_winners = winners
                                group_4_prize = prize
                            elif 'Group 5' in group:
                                group_5_winners = winners
                                group_5_prize = prize
                            elif 'Group 6' in group:
                                group_6_winners = winners
                                group_6_prize = prize
                            elif 'Group 7' in group:
                                group_7_winners = winners
                                group_7_prize = prize
                
                # Get jackpot amount if available
                jackpot_div = block.find('div', class_='est-jackpot')
                jackpot_amount = None
                if jackpot_div:
                    jackpot_text = jackpot_div.text.strip()
                    jackpot_match = re.search(r'\$([0-9,]+)', jackpot_text)
                    if jackpot_match:
                        jackpot_amount = float(jackpot_match.group(1).replace(',', ''))
                
                # Only process results for the specified dates if provided
                if dates_to_scrape is None or draw_date in dates_to_scrape:
                    results.append({
                        'draw_date': draw_date,
                        'draw_number': int(draw_number),
                        'winning_numbers': winning_numbers,
                        'additional_number': additional_number,
                        'group_1_winners': group_1_winners,
                        'group_1_prize': group_1_prize,
                        'group_2_winners': group_2_winners,
                        'group_2_prize': group_2_prize,
                        'group_3_winners': group_3_winners,
                        'group_3_prize': group_3_prize,
                        'group_4_winners': group_4_winners,
                        'group_4_prize': group_4_prize,
                        'group_5_winners': group_5_winners,
                        'group_5_prize': group_5_prize,
                        'group_6_winners': group_6_winners,
                        'group_6_prize': group_6_prize,
                        'group_7_winners': group_7_winners,
                        'group_7_prize': group_7_prize,
                        'jackpot_amount': jackpot_amount
                    })
            except Exception as e:
                st.error(f"Error processing a result block: {str(e)}")
                continue
        
        # Create DataFrame from results
        df = pd.DataFrame(results)
        
        # If we need to scrape more historical data that's not on the first page
        # We would need to implement pagination logic here
        # This implementation only scrapes what's visible on the main page
        
        return df
    
    except Exception as e:
        st.error(f"Error scraping TOTO results: {str(e)}")
        return pd.DataFrame()
