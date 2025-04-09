import os
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ARRAY, Table, MetaData, select, insert
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import streamlit as st

# Get database connection string from environment variable
DATABASE_URL = os.environ.get('DATABASE_URL')

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Create metadata object
metadata = MetaData()

# Define toto_results table
toto_results = Table(
    'toto_results', 
    metadata,
    Column('id', Integer, primary_key=True),
    Column('draw_number', Integer, unique=True, nullable=False),
    Column('draw_date', Date, nullable=False),
    Column('winning_numbers', ARRAY(Integer), nullable=False),
    Column('additional_number', Integer, nullable=False),
    Column('group_1_winners', Integer),
    Column('group_1_prize', Float),
    Column('group_2_winners', Integer),
    Column('group_2_prize', Float),
    Column('group_3_winners', Integer),
    Column('group_3_prize', Float),
    Column('group_4_winners', Integer),
    Column('group_4_prize', Float),
    Column('group_5_winners', Integer),
    Column('group_5_prize', Float),
    Column('group_6_winners', Integer),
    Column('group_6_prize', Float),
    Column('group_7_winners', Integer),
    Column('group_7_prize', Float),
    Column('estimated_jackpot', Float),
    Column('cascade_amount', Float),
    Column('query_string', String)
)

def initialize_database(silent=True):
    """
    Initialize the database by creating tables if they don't exist
    
    Args:
        silent: If True, don't display success/error messages
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create tables
        metadata.create_all(engine)
        if not silent:
            st.success("Database initialized successfully")
        return True
    except Exception as e:
        if not silent:
            st.error(f"Error initializing database: {str(e)}")
        return False

def load_database():
    """
    Load the TOTO results from the database into a pandas DataFrame
    
    Returns:
        DataFrame containing TOTO results, or None if table doesn't exist or is empty
    """
    try:
        # Check if the table exists
        with engine.connect() as connection:
            if not engine.dialect.has_table(connection, 'toto_results'):
                print("Database table doesn't exist yet. Initializing...")
                st.warning("Database table doesn't exist yet. Will create it.")
                initialize_database()
                return None
        
        print("Database table exists, querying records...")
        
        # Query all records from toto_results table
        query = select(toto_results)
        with engine.connect() as connection:
            result = connection.execute(query)
            # Convert to DataFrame
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        if df.empty:
            print("Database is empty")
            st.info("Database is empty")
            return None
        
        # Convert date string to datetime
        if 'draw_date' in df.columns:
            df['draw_date'] = pd.to_datetime(df['draw_date'])
        
        print(f"Successfully loaded {len(df)} records from database")
        st.success(f"Loaded {len(df)} records from database")
        return df
        
    except Exception as e:
        print(f"Error loading database: {str(e)}")
        st.error(f"Error loading database: {str(e)}")
        return None

def save_database(df):
    """
    Save the TOTO results to the database
    
    Args:
        df: DataFrame containing TOTO results
    """
    try:
        if df is None or df.empty:
            st.warning("No data to save to database")
            return False
        
        # Make sure the database is initialized
        with engine.connect() as conn:
            if not engine.dialect.has_table(conn, 'toto_results'):
                print("Table 'toto_results' doesn't exist, initializing...")
                initialize_database()
                print("Database initialized.")
        
        # Log some information for debugging
        print(f"Attempting to save {len(df)} records to database")
        print(f"DataFrame columns: {df.columns.tolist()}")
        print(f"First row sample: {df.iloc[0].to_dict()}")
        
        # Prepare data for insertion
        records = []
        for _, row in df.iterrows():
            try:
                # Convert pandas timestamp to date
                if isinstance(row['draw_date'], pd.Timestamp):
                    draw_date = row['draw_date'].date()
                else:
                    draw_date = row['draw_date']
                
                # Create record dictionary with proper type conversion and validation
                record = {
                    'draw_number': int(row['draw_number']),
                    'draw_date': draw_date,
                    'winning_numbers': row['winning_numbers'],
                    'additional_number': int(row['additional_number']),
                    'group_1_winners': int(row['group_1_winners']) if pd.notna(row['group_1_winners']) else 0,
                    'group_1_prize': float(row['group_1_prize']) if pd.notna(row['group_1_prize']) else 0.0,
                    'group_2_winners': int(row['group_2_winners']) if pd.notna(row['group_2_winners']) else 0,
                    'group_2_prize': float(row['group_2_prize']) if pd.notna(row['group_2_prize']) else 0.0,
                    'group_3_winners': int(row['group_3_winners']) if pd.notna(row['group_3_winners']) else 0,
                    'group_3_prize': float(row['group_3_prize']) if pd.notna(row['group_3_prize']) else 0.0,
                    'group_4_winners': int(row['group_4_winners']) if pd.notna(row['group_4_winners']) else 0,
                    'group_4_prize': float(row['group_4_prize']) if pd.notna(row['group_4_prize']) else 0.0,
                    'group_5_winners': int(row['group_5_winners']) if pd.notna(row['group_5_winners']) else 0,
                    'group_5_prize': float(row['group_5_prize']) if pd.notna(row['group_5_prize']) else 0.0,
                    'group_6_winners': int(row['group_6_winners']) if pd.notna(row['group_6_winners']) else 0,
                    'group_6_prize': float(row['group_6_prize']) if pd.notna(row['group_6_prize']) else 0.0,
                    'group_7_winners': int(row['group_7_winners']) if pd.notna(row['group_7_winners']) else 0,
                    'group_7_prize': float(row['group_7_prize']) if pd.notna(row['group_7_prize']) else 0.0,
                    'estimated_jackpot': float(row['estimated_jackpot']) if 'estimated_jackpot' in row and pd.notna(row['estimated_jackpot']) else 0.0,
                    'cascade_amount': float(row['cascade_amount']) if 'cascade_amount' in row and pd.notna(row['cascade_amount']) else 0.0,
                    'query_string': str(row['query_string']) if 'query_string' in row and row['query_string'] is not None else ''
                }
                records.append(record)
                
            except Exception as e:
                print(f"Error processing row: {e}")
                print(f"Problematic row: {row}")
                continue
        
        print(f"Processed {len(records)} valid records for database insertion")
        if not records:
            st.error("No valid records to save to database")
            return False
            
        # Start a transaction
        connection = engine.connect()
        transaction = connection.begin()
        
        try:
            # Insert each record with update on conflict
            for record in records:
                try:
                    # Debug information
                    print(f"Processing record for draw #{record['draw_number']}")
                    
                    # Check if record already exists
                    query = select(toto_results).where(toto_results.c.draw_number == record['draw_number'])
                    result = connection.execute(query).fetchone()
                    
                    if not result:
                        # Insert new record
                        print(f"Inserting new record for draw #{record['draw_number']}")
                        connection.execute(toto_results.insert().values(**record))
                    else:
                        # Update existing record
                        print(f"Updating existing record for draw #{record['draw_number']}")
                        connection.execute(
                            toto_results.delete().where(toto_results.c.draw_number == record['draw_number'])
                        )
                        connection.execute(toto_results.insert().values(**record))
                except Exception as e:
                    print(f"Error with record {record['draw_number']}: {str(e)}")
                    # Continue with the next record rather than failing the entire transaction
                    continue
            
            # Commit the transaction
            transaction.commit()
            st.success(f"Saved {len(records)} records to database")
            return True
            
        except Exception as e:
            # Rollback the transaction on error
            transaction.rollback()
            st.error(f"Error during database transaction: {str(e)}")
            print(f"Transaction error: {str(e)}")
            return False
            
    except Exception as e:
        st.error(f"Error saving to database: {str(e)}")
        print(f"Overall save error: {str(e)}")
        return False

def migrate_from_pickle():
    """
    Migrate data from the pickle file to the PostgreSQL database
    """
    import pickle
    import os
    
    try:
        if not os.path.exists('toto_database.pkl'):
            st.warning("No pickle file found to migrate")
            return False
        
        # Load data from pickle file
        with open('toto_database.pkl', 'rb') as f:
            df = pickle.load(f)
        
        if df is None or df.empty:
            st.warning("Pickle file exists but contains no data")
            return False
        
        # Save data to database
        st.info(f"Migrating {len(df)} records from pickle file to database")
        success = save_database(df)
        
        if success:
            st.success("Migration from pickle file to database completed successfully")
            # Option to rename the pickle file as backup
            os.rename('toto_database.pkl', 'toto_database.pkl.bak')
            st.info("Original pickle file renamed to toto_database.pkl.bak")
            return True
        else:
            st.error("Failed to migrate data to database")
            return False
        
    except Exception as e:
        st.error(f"Error during migration: {str(e)}")
        return False

# Test connection function
def test_connection():
    """Test the database connection and report status"""
    try:
        with engine.connect() as connection:
            return True, "Successfully connected to PostgreSQL database"
    except Exception as e:
        return False, f"Failed to connect to PostgreSQL database: {str(e)}"

def check_database_state():
    """
    Check database state and return information about the connection, table, and records
    
    Returns:
        Dictionary containing database state information
    """
    state = {
        'connection': {
            'success': False,
            'message': ''
        },
        'table_exists': False,
        'record_count': 0,
        'sample_record': None
    }
    
    try:
        # Check if connection works
        success, message = test_connection()
        state['connection']['success'] = success
        state['connection']['message'] = message
        
        if not success:
            return state
            
        # Check if the table exists
        with engine.connect() as connection:
            exists = engine.dialect.has_table(connection, 'toto_results')
            state['table_exists'] = exists
            
            if exists:
                # Check table contents
                query = select(toto_results)
                result = connection.execute(query).fetchall()
                state['record_count'] = len(result)
                
                if len(result) > 0:
                    # Get a sample record
                    state['sample_record'] = {column: str(value) for column, value in zip(result[0].keys(), result[0])}
        
        return state
    except Exception as e:
        print(f"Error checking database state: {str(e)}")
        state['connection']['message'] = f"Error: {str(e)}"
        return state

def debug_database():
    """Debug function to check database state and print to console"""
    try:
        # Check database state
        state = check_database_state()
        
        # Print state information
        print(f"Database connection: {state['connection']['success']}, Message: {state['connection']['message']}")
        print(f"Table 'toto_results' exists: {state['table_exists']}")
        
        if state['table_exists']:
            print(f"Number of records in database: {state['record_count']}")
            
            if state['sample_record']:
                print(f"Sample record (first row): {state['sample_record']}")
        
        return True
    except Exception as e:
        print(f"Error during database debugging: {str(e)}")
        return False