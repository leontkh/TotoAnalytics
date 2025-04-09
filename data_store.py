import pandas as pd
import pickle
import os
import json
from datetime import datetime

def save_data(data, filename):
    """
    Save data to a file
    
    Args:
        data: Data to save
        filename: Name of the file to save to
    """
    _, file_extension = os.path.splitext(filename)
    
    try:
        if file_extension == '.pkl':
            with open(filename, 'wb') as f:
                pickle.dump(data, f)
        elif file_extension == '.csv':
            data.to_csv(filename, index=False)
        elif file_extension == '.json':
            with open(filename, 'w') as f:
                json.dump(data, f)
        else:
            raise ValueError(f"Unsupported file extension: {file_extension}")
    except Exception as e:
        print(f"Error saving data to {filename}: {str(e)}")

def load_data(filename):
    """
    Load data from a file
    
    Args:
        filename: Name of the file to load from
    
    Returns:
        Loaded data
    """
    if not os.path.exists(filename):
        return None
    
    _, file_extension = os.path.splitext(filename)
    
    try:
        if file_extension == '.pkl':
            with open(filename, 'rb') as f:
                return pickle.load(f)
        elif file_extension == '.csv':
            return pd.read_csv(filename)
        elif file_extension == '.json':
            with open(filename, 'r') as f:
                return json.load(f)
        else:
            raise ValueError(f"Unsupported file extension: {file_extension}")
    except Exception as e:
        print(f"Error loading data from {filename}: {str(e)}")
        return None

def append_data(new_data, filename):
    """
    Append new data to existing data file
    
    Args:
        new_data: New data to append
        filename: Name of the file to append to
    
    Returns:
        Combined data
    """
    existing_data = load_data(filename)
    
    if existing_data is None:
        combined_data = new_data
    elif isinstance(existing_data, pd.DataFrame) and isinstance(new_data, pd.DataFrame):
        combined_data = pd.concat([existing_data, new_data], ignore_index=True)
        combined_data = combined_data.drop_duplicates()
    else:
        # For other data types, this would need custom handling
        return None
    
    save_data(combined_data, filename)
    return combined_data
