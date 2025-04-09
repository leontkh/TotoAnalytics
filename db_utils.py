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

def initialize_database():
    """
    Initialize the database by creating tables if they don't exist
    """
    try:
        # Create tables
        metadata.create_all(engine)
        st.success("Database initialized successfully")
        return True
    except Exception as e:
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
        if not engine.dialect.has_table(engine.connect(), 'toto_results'):
            st.warning("Database table doesn't exist yet. Will create it.")
            initialize_database()
            return None
        
        # Query all records from toto_results table
        query = select([toto_results])
        result = engine.connect().execute(query)
        
        # Convert to DataFrame
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        if df.empty:
            st.info("Database is empty")
            return None
        
        # Convert date string to datetime
        if 'draw_date' in df.columns:
            df['draw_date'] = pd.to_datetime(df['draw_date'])
        
        st.success(f"Loaded {len(df)} records from database")
        return df
        
    except Exception as e:
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
        if not engine.dialect.has_table(engine.connect(), 'toto_results'):
            initialize_database()
        
        # Prepare data for insertion
        records = []
        for _, row in df.iterrows():
            # Convert pandas timestamp to date
            if isinstance(row['draw_date'], pd.Timestamp):
                draw_date = row['draw_date'].date()
            else:
                draw_date = row['draw_date']
            
            # Create record dictionary
            record = {
                'draw_number': int(row['draw_number']),
                'draw_date': draw_date,
                'winning_numbers': row['winning_numbers'],
                'additional_number': int(row['additional_number']),
                'group_1_winners': int(row['group_1_winners']) if pd.notna(row['group_1_winners']) else None,
                'group_1_prize': float(row['group_1_prize']) if pd.notna(row['group_1_prize']) else None,
                'group_2_winners': int(row['group_2_winners']) if pd.notna(row['group_2_winners']) else None,
                'group_2_prize': float(row['group_2_prize']) if pd.notna(row['group_2_prize']) else None,
                'group_3_winners': int(row['group_3_winners']) if pd.notna(row['group_3_winners']) else None,
                'group_3_prize': float(row['group_3_prize']) if pd.notna(row['group_3_prize']) else None,
                'group_4_winners': int(row['group_4_winners']) if pd.notna(row['group_4_winners']) else None,
                'group_4_prize': float(row['group_4_prize']) if pd.notna(row['group_4_prize']) else None,
                'group_5_winners': int(row['group_5_winners']) if pd.notna(row['group_5_winners']) else None,
                'group_5_prize': float(row['group_5_prize']) if pd.notna(row['group_5_prize']) else None,
                'group_6_winners': int(row['group_6_winners']) if pd.notna(row['group_6_winners']) else None,
                'group_6_prize': float(row['group_6_prize']) if pd.notna(row['group_6_prize']) else None,
                'group_7_winners': int(row['group_7_winners']) if pd.notna(row['group_7_winners']) else None,
                'group_7_prize': float(row['group_7_prize']) if pd.notna(row['group_7_prize']) else None,
                'estimated_jackpot': float(row['estimated_jackpot']) if 'estimated_jackpot' in row and pd.notna(row['estimated_jackpot']) else None,
                'cascade_amount': float(row['cascade_amount']) if 'cascade_amount' in row and pd.notna(row['cascade_amount']) else None,
                'query_string': row['query_string'] if 'query_string' in row else None
            }
            records.append(record)
        
        # Start a transaction
        connection = engine.connect()
        transaction = connection.begin()
        
        try:
            # Insert each record with update on conflict
            for record in records:
                # Check if record already exists
                query = select([toto_results]).where(toto_results.c.draw_number == record['draw_number'])
                result = connection.execute(query).fetchone()
                
                if not result:
                    # Insert new record
                    connection.execute(toto_results.insert().values(**record))
                else:
                    # Update existing record (delete and reinsert since we don't have a proper upsert with SQLAlchemy Core)
                    connection.execute(
                        toto_results.delete().where(toto_results.c.draw_number == record['draw_number'])
                    )
                    connection.execute(toto_results.insert().values(**record))
            
            # Commit the transaction
            transaction.commit()
            st.success(f"Saved {len(records)} records to database")
            return True
            
        except Exception as e:
            # Rollback the transaction on error
            transaction.rollback()
            st.error(f"Error during database transaction: {str(e)}")
            return False
            
    except Exception as e:
        st.error(f"Error saving to database: {str(e)}")
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