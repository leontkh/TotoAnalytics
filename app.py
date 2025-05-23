import streamlit as st
import pandas as pd
import os
import datetime
from scraper import scrape_toto_results
from data_utils import get_missing_draw_dates, get_missing_query_strings
from calculator import calculate_prize_pools
from visualization import (
    plot_winning_numbers_frequency,
    plot_prize_pool_trend,
    plot_winning_numbers_heatmap,
    plot_group_prize_distribution
)
from db_utils import (
    load_database, 
    save_database, 
    initialize_database, 
    migrate_from_pickle,
    test_connection,
    debug_database,
    check_database_state,
    engine,
    toto_results,
    select
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

# Check database connection and initialize if needed
if not 'db_initialized' in st.session_state:
    db_success, db_message = test_connection()
    if not db_success:
        # Only initialize if connection failed and not already tried
        initialize_database()
    st.session_state.db_initialized = True

# Sidebar
st.sidebar.title("Controls")
update_data = st.sidebar.button("Update Database")

# Add a debug button
debug_btn = st.sidebar.button("Debug Database")
if debug_btn:
    # Run database debug function and show detailed results
    with st.expander("Database Debug Information", expanded=True):
        st.write("Debugging PostgreSQL database...")
        
        # Run the debug function (outputs to console)
        debug_database()
        
        # Get database state
        db_state = check_database_state()
        
        # Display in nice UI
        st.write(f"Database connection: {'✅ Success' if db_state['connection']['success'] else '❌ Failed'}")
        st.write(f"Message: {db_state['connection']['message']}")
        st.write(f"Table 'toto_results' exists: {'✅ Yes' if db_state['table_exists'] else '❌ No'}")
        
        if db_state['table_exists']:
            st.write(f"Number of records in database: {db_state['record_count']}")
            
            if db_state['sample_record']:
                st.write("Sample record (first row):")
                st.json(db_state['sample_record'])
        
        # Try to initialize database if needed
        if not db_state['table_exists'] or db_state['record_count'] == 0:
            st.write("Attempting to initialize database...")
            success = initialize_database(silent=False)
            st.write(f"Database initialization: {'✅ Success' if success else '❌ Failed'}")
            
            # Check if database is loaded in memory
            if st.session_state.toto_data is not None:
                st.write(f"Data loaded in memory: {len(st.session_state.toto_data)} records")
                
                if len(st.session_state.toto_data) > 0 and db_state['record_count'] == 0:
                    st.warning("Data exists in memory but not in database. Attempting to save...")
                    
                    # Try to save the data
                    try:
                        save_success = save_database(st.session_state.toto_data)
                        if save_success:
                            st.success(f"Successfully saved {len(st.session_state.toto_data)} records to database")
                        else:
                            st.error("Failed to save data to database")
                    except Exception as e:
                        st.error(f"Error saving data: {str(e)}")
            else:
                st.warning("No data loaded in memory")

if update_data:
    with st.spinner("Updating database with latest TOTO results..."):
        # Get query strings for missing draws
        st.write("Fetching available query strings...")
        
        if st.session_state.toto_data is not None:
            st.write(f"Current database has {len(st.session_state.toto_data)} entries")
            # Display the oldest and newest draws in the database
            oldest_date = st.session_state.toto_data['draw_date'].min()
            newest_date = st.session_state.toto_data['draw_date'].max()
            st.write(f"Date range: {oldest_date} to {newest_date}")
        else:
            st.write("No existing database found, will create new one")
            
        # Get query strings for draws not already in the database
        query_strings = get_missing_draw_dates(st.session_state.toto_data)
        
        if query_strings:
            st.info(f"Found {len(query_strings)} query strings to process. Scraping data...")
            # Just to confirm the query strings in UI
            if len(query_strings) > 5:
                st.write(f"Query strings to process: {query_strings[:5]} and {len(query_strings)-5} more...")
            else:
                st.write(f"Query strings to process: {query_strings}")
                
            # Process each query string one by one
            results_dataframes = []
            batch_size = 10  # Process in batches to avoid overwhelming the UI
            total_batches = (len(query_strings) + batch_size - 1) // batch_size
            
            st.info(f"Will process all {len(query_strings)} query strings in {total_batches} batches of {batch_size} each")
            
            # Create a progress bar
            progress_bar = st.progress(0)
            
            for batch_idx in range(total_batches):
                batch_start = batch_idx * batch_size
                batch_end = min(batch_start + batch_size, len(query_strings))
                current_batch = query_strings[batch_start:batch_end]
                
                st.write(f"Processing batch {batch_idx+1}/{total_batches} ({batch_end-batch_start} query strings)")
                
                for i, query_string in enumerate(current_batch):
                    overall_idx = batch_start + i
                    progress = min(100, int((overall_idx + 1) / len(query_strings) * 100))
                    progress_bar.progress(progress)
                    
                    st.write(f"Processing query string {overall_idx+1}/{len(query_strings)}: {query_string}")
                    
                    # Scrape TOTO results using the query string
                    st.write("Starting scraper...")
                    single_draw_data = scrape_toto_results(query_string)
                    
                    if single_draw_data is not None and not single_draw_data.empty:
                        st.write(f"Successfully scraped draw with query string: {query_string}")
                        st.write(f"DataFrame shape: {single_draw_data.shape}")
                        results_dataframes.append(single_draw_data)
                    else:
                        st.warning(f"Failed to scrape data for query string: {query_string}")
                
                # If we're not on the last batch, show a partial update
                if batch_idx < total_batches - 1 and results_dataframes:
                    st.info(f"Batch {batch_idx+1} complete. Scraped {len(results_dataframes)} draws so far.")
                    
                    # Optionally save the partial results every few batches
                    if (batch_idx + 1) % 5 == 0:
                        try:
                            partial_data = pd.concat(results_dataframes, ignore_index=True)
                            partial_data_with_pools = calculate_prize_pools(partial_data)
                            
                            if st.session_state.toto_data is not None:
                                interim_combined = pd.concat([st.session_state.toto_data, partial_data_with_pools], ignore_index=True)
                                interim_combined = interim_combined.drop_duplicates(subset=['draw_date', 'draw_number'], keep='last')
                            else:
                                interim_combined = partial_data_with_pools
                            
                            st.session_state.toto_data = interim_combined
                            save_database(interim_combined)
                            st.session_state.last_updated = datetime.datetime.now()
                            st.success(f"Saved intermediate results with {len(partial_data)} draws")
                        except Exception as e:
                            st.warning(f"Could not save intermediate results: {str(e)}")
            
            # Completed all batches
            st.success(f"Completed processing {len(query_strings)} query strings")
            
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
        # Convert timestamp to string to avoid errors
        earliest_date = pd.to_datetime(st.session_state.toto_data['draw_date']).min()
        st.metric("Earliest Record", earliest_date.strftime('%Y-%m-%d'))
    
    with col2:
        # Convert timestamp to string to avoid errors
        latest_date = pd.to_datetime(st.session_state.toto_data['draw_date']).max()
        st.metric("Latest Draw", latest_date.strftime('%Y-%m-%d'))
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
