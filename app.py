import streamlit as st
import pandas as pd
import os
import datetime
from scraper import scrape_toto_results
from data_utils import load_database, save_database, get_missing_draw_dates, get_missing_query_strings
from calculator import calculate_prize_pools
from visualization import (
    plot_winning_numbers_frequency,
    plot_prize_pool_trend,
    plot_winning_numbers_heatmap,
    plot_group_prize_distribution
)

# Set page config
st.set_page_config(
    page_title="Singapore Pools TOTO Analysis",
    page_icon="🎮",
    layout="wide"
)

# Initialize session state for storing data
if 'toto_data' not in st.session_state:
    st.session_state.toto_data = load_database()

if 'last_updated' not in st.session_state:
    st.session_state.last_updated = None

# Title and description
st.title("Singapore Pools TOTO Analysis Dashboard")
st.markdown("""
This application scrapes Singapore Pools TOTO results, calculates prize pools, 
and provides analytics on historical data.
""")

# Sidebar
st.sidebar.title("Controls")
update_data = st.sidebar.button("Update Database")

if update_data:
    with st.spinner("Updating database with latest TOTO results..."):
        # Get query strings for missing draws
        st.write("Fetching available query strings...")
        
        if st.session_state.toto_data is not None:
            st.write(f"Current database has {len(st.session_state.toto_data)} entries")
        else:
            st.write("No existing database found, will create new one")
            
        query_strings = get_missing_query_strings()
        
        if query_strings:
            st.info(f"Found {len(query_strings)} query strings to process. Scraping data...")
            # Just to confirm the query strings in UI
            if len(query_strings) > 5:
                st.write(f"Query strings to process: {query_strings[:5]} and {len(query_strings)-5} more...")
            else:
                st.write(f"Query strings to process: {query_strings}")
                
            # Process each query string one by one
            results_dataframes = []
            
            for i, query_string in enumerate(query_strings[:5]):  # Process first 5 for testing
                st.write(f"Processing query string {i+1}/{min(5, len(query_strings))}: {query_string}")
                
                # Scrape TOTO results using the query string
                st.write("Starting scraper...")
                single_draw_data = scrape_toto_results(query_string)
                
                if single_draw_data is not None and not single_draw_data.empty:
                    st.write(f"Successfully scraped draw with query string: {query_string}")
                    st.write(f"DataFrame shape: {single_draw_data.shape}")
                    results_dataframes.append(single_draw_data)
                else:
                    st.warning(f"Failed to scrape data for query string: {query_string}")
            
            # Combine all dataframes
            if results_dataframes:
                new_data = pd.concat(results_dataframes, ignore_index=True)
                st.write(f"Combined {len(results_dataframes)} draws into a DataFrame with shape: {new_data.shape}")
                
                if not new_data.empty:
                    # Calculate prize pools for new data
                    st.write("Calculating prize pools...")
                    try:
                        new_data_with_pools = calculate_prize_pools(new_data)
                        st.write(f"Prize pool calculation completed. Shape: {new_data_with_pools.shape}")
                        
                        # Merge with existing data
                        if st.session_state.toto_data is not None:
                            st.write("Merging with existing data...")
                            combined_data = pd.concat([st.session_state.toto_data, new_data_with_pools], ignore_index=True)
                            combined_data = combined_data.drop_duplicates(subset=['draw_date', 'draw_number'], keep='last')
                        else:
                            combined_data = new_data_with_pools
                        
                        st.write(f"Final database shape: {combined_data.shape}")
                        
                        # Save the data
                        st.write("Saving database...")
                        st.session_state.toto_data = combined_data
                        save_database(combined_data)
                        st.session_state.last_updated = datetime.datetime.now()
                        st.success(f"Database updated with {len(new_data)} new draw results.")
                    except Exception as e:
                        st.error(f"Error during prize pool calculation or data saving: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
                else:
                    st.error("Combined DataFrame is empty.")
            else:
                st.error("Failed to scrape any data from the provided query strings.")
        else:
            st.warning("No query strings found. Unable to fetch new data.")
            
            # As a fallback, try to fetch the latest draw
            st.info("Trying to fetch the latest draw as a fallback...")
            latest_draw = scrape_toto_results(None)  # None will fetch the latest draw
            
            if latest_draw is not None and not latest_draw.empty:
                st.success("Successfully fetched the latest draw.")
                
                # Calculate prize pools
                try:
                    latest_draw_with_pools = calculate_prize_pools(latest_draw)
                    
                    # Merge with existing data
                    if st.session_state.toto_data is not None:
                        combined_data = pd.concat([st.session_state.toto_data, latest_draw_with_pools], ignore_index=True)
                        combined_data = combined_data.drop_duplicates(subset=['draw_date', 'draw_number'], keep='last')
                    else:
                        combined_data = latest_draw_with_pools
                    
                    # Save the data
                    st.session_state.toto_data = combined_data
                    save_database(combined_data)
                    st.session_state.last_updated = datetime.datetime.now()
                    st.success("Database updated with the latest draw.")
                except Exception as e:
                    st.error(f"Error processing latest draw: {str(e)}")
            else:
                st.error("Failed to fetch the latest draw. Database remains unchanged.")
    
    # Use st.rerun to refresh the page after update
    st.rerun()

# Display last updated time
if st.session_state.last_updated:
    st.sidebar.text(f"Last updated: {st.session_state.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")

# Main content
if st.session_state.toto_data is not None and not st.session_state.toto_data.empty:
    # Display summary statistics
    st.header("Summary Statistics")
    
    # Create two columns for stats
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Draws", len(st.session_state.toto_data))
        st.metric("Earliest Record", st.session_state.toto_data['draw_date'].min())
    
    with col2:
        st.metric("Latest Draw", st.session_state.toto_data['draw_date'].max())
        st.metric("Average Group 1 Prize", f"${st.session_state.toto_data['group_1_prize'].mean():,.2f}")

    # Data exploration
    st.header("Data Exploration")
    
    # Allow selection of date range
    min_date = pd.to_datetime(st.session_state.toto_data['draw_date']).min().date()
    max_date = pd.to_datetime(st.session_state.toto_data['draw_date']).max().date()
    
    date_col1, date_col2 = st.columns(2)
    with date_col1:
        start_date = st.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
    with date_col2:
        end_date = st.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
    
    # Filter data based on selected date range
    filtered_data = st.session_state.toto_data[
        (pd.to_datetime(st.session_state.toto_data['draw_date']).dt.date >= start_date) &
        (pd.to_datetime(st.session_state.toto_data['draw_date']).dt.date <= end_date)
    ]
    
    # Display visualizations
    st.header("Visualizations")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Winning Numbers", "Prize Trends", "Number Patterns", "Prize Distribution"])
    
    with tab1:
        st.subheader("Winning Numbers Frequency")
        fig_freq = plot_winning_numbers_frequency(filtered_data)
        st.plotly_chart(fig_freq, use_container_width=True)
    
    with tab2:
        st.subheader("Prize Pool Trends")
        fig_trend = plot_prize_pool_trend(filtered_data)
        st.plotly_chart(fig_trend, use_container_width=True)
    
    with tab3:
        st.subheader("Winning Numbers Heatmap")
        fig_heatmap = plot_winning_numbers_heatmap(filtered_data)
        st.plotly_chart(fig_heatmap, use_container_width=True)
    
    with tab4:
        st.subheader("Group Prize Distribution")
        fig_distribution = plot_group_prize_distribution(filtered_data)
        st.plotly_chart(fig_distribution, use_container_width=True)

    # Raw data exploration
    st.header("Raw Data")
    if st.checkbox("Show raw data"):
        st.dataframe(filtered_data.sort_values(by='draw_date', ascending=False), use_container_width=True)

else:
    st.warning("No data available. Please click the 'Update Database' button to fetch TOTO results.")

# Footer
st.markdown("---")
st.markdown(
    "This app scrapes data from Singapore Pools and calculates prize pools based on the TOTO prize structure. "
    "It is for informational purposes only."
)
