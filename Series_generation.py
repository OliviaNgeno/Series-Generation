# ### Series generation automation
# 
# User will provide:
# 
#     - path to yaml specification file, yaml_file_path
#     - path to exhibit database exhibit_db_path
#     - date columns to be updated each month
#     - static columns to maintain for existing records


# Required Libraries
import pandas as pd
from exhibit import exhibit as xbt
from exhibit.core.spec import (
    Spec, UUIDColumn, CategoricalColumn, NumericalColumn, DateColumn)
from exhibit.db import db_util
import yaml
from sklearn.utils import shuffle  
import copy
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import sqlite3
from fractions import Fraction
import logging
import argparse

# Create the parser
parser = argparse.ArgumentParser(description="Series Generation")



parser.add_argument('--specification', help='Path to specification YAML file')
parser.add_argument('--user_input', help='Path to user input YAML file')



args = parser.parse_args()

# Configuring the logger
logging.basicConfig(
    level=logging.INFO,  # minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',  # format of log messages
    handlers=[
        logging.FileHandler("app.log"),  # Log to file
        logging.StreamHandler()  # log to console
    ]
)

# logger object
logger = logging.getLogger(__name__)


# Inputs

spec_file_path = args.specification # path to spec yaml
input_file_path = args.user_input # path to input


# function to load a YAML specification file provided by user
# Accepts path to YAML
# All fields in YAML such as distribution parameters must be set according to Exhibit rules

def load_yaml_to_spec_dict(yaml_file_path):
    try:
        with open(yaml_file_path, encoding="utf-8") as f:
            spec_dict = yaml.safe_load(f)
        logger.info("YAML file successfully loaded.")
        return spec_dict
    except Exception as e:
        logger.error(f"Error loading YAML file: {e}")
        return None



# function to load a YAML file with user inputs
# Accepts path to YAML

def load_user_inputs(yaml_file_path):
    try:
        with open(yaml_file_path, 'r') as f:
            user_inputs = yaml.safe_load(f)
        logger.info("User Input successfully loaded.")
        return user_inputs
    except Exception as e:
        logger.error(f"Error loading User YAML file: {e}")
        return None



# generation of the initial records with specification dictionary as provided
# followed by insertion into the Exhibit database as a reference table for future use

def generate_first_period(spec_dict):
    exhibit_data = xbt.Exhibit(command="fromspec", source=spec_dict, linked_columns = linked_columns, output="dataframe")
    initial_data_df = exhibit_data.generate()
    db_util.insert_table(initial_data_df, reference_table) # initial load saved in the database
    logger.info(f"Generated {len(initial_data_df)} new records for first period.")
    return initial_data_df



def update_dates(current_start_date, current_end_date, period, length_of_period):
    """
    Updates the current start and end dates based on the period (days, weeks, months)
    and the length_of_period (e.g., every 5 days, 2 weeks, etc.)

    Args:
    - current_start_date (date): The current start date.
    - current_end_date (date): The current end date.
    - period (str): The period of updates (days, weeks, months).
    - length_of_period (int): The length of updates (e.g., every 5 days, 2 weeks, 1 month).

    Returns:
    - next_start_date (date): The updated start date.
    - next_end_date (date): The updated end date.
    """

    current_start_date = datetime.strptime(current_start_date, "%Y-%m-%d")
    current_end_date = datetime.strptime(current_end_date, "%Y-%m-%d")

    # Update based on period
    if period == 'days':
        delta = timedelta(days=length_of_period)
    elif period == 'weeks':
        delta = timedelta(weeks=length_of_period)
    elif period == 'months':
        delta = relativedelta(months=length_of_period)
    else:
        raise ValueError("Invalid period. Choose from 'days', 'weeks', or 'months'.")

    # Update the dates
    next_start_date = current_start_date + delta
    next_end_date = current_end_date + delta

    return next_start_date.strftime("%Y-%m-%d"), next_end_date.strftime("%Y-%m-%d")


# In[8]:


# first part of periodic generation
# generating new records
# apply a new random seed for new unique identifiers
# new columns is half of dataset (to be refined)
# handle date adjustions

def generate_new_records(new_spec_dict):
    new_spec_dict["metadata"]["random_seed"] += 1  # Increment for each month
    new_spec_dict["metadata"]["number_of_rows"] = num_new_records  # Expected number of rows for new records

    # updating uuid seed
    for uuid in uuid_columns:
        if "uuid_seed" in new_spec_dict["columns"][uuid]:
            new_spec_dict["columns"][uuid]["uuid_seed"] += 1 
    
    # updating dates
    for date_column in date_columns:
        if date_column in new_spec_dict["columns"]:
            current_start_date = new_spec_dict["columns"][date_column]["from"]
            current_end_date = new_spec_dict["columns"][date_column]["to"]
            new_start_date, new_end_date = update_dates(current_start_date, current_end_date, period, length_of_period)
            new_spec_dict["columns"][date_column]["from"] = new_start_date
            new_spec_dict["columns"][date_column]["to"] = new_end_date
    # generation with exhibit
    exhibit_data = xbt.Exhibit(command="fromspec", source=new_spec_dict, linked_columns = linked_columns, output="dataframe")
    new_data_df = exhibit_data.generate()
    logger.info(f"Generated {len(new_data_df)} new records.")
    return new_data_df, new_spec_dict


# In[9]:


# updating already existing records
# drawing from reference table
# using anonymising set in categorical columns where you can provide a table to draw from
# unique identifier columns set as categorical columns with the anonymizing set as the reference table
# handle static columns by pairing with a uuid in reference
# update the rest of columns

def generate_existing_records(existing_spec_dict):
    existing_spec_dict["metadata"]["random_seed"] += 1  # Increment for each month
    existing_spec_dict["metadata"]["number_of_rows"] = num_existing_records  # Expected number of rows for new records

    for date_column in date_columns:
        if date_column in existing_spec_dict["columns"]:
            current_start_date = existing_spec_dict["columns"][date_column]["from"]
            current_end_date = existing_spec_dict["columns"][date_column]["to"]
            new_start_date, new_end_date = update_dates(current_start_date, current_end_date, period, length_of_period)
            existing_spec_dict["columns"][date_column]["from"] = new_start_date
            existing_spec_dict["columns"][date_column]["to"] = new_end_date

    for i, uuid in enumerate(uuid_columns):
        if uuid in existing_spec_dict["columns"]:
            if "uuid_columns" in existing_spec_dict["metadata"]:         
                existing_spec_dict["metadata"]["uuid_columns"].remove(uuid)
    
            if "categorical_columns" not in existing_spec_dict["metadata"]:         
                existing_spec_dict["metadata"]["categorical_columns"] = []     
            
            existing_spec_dict["metadata"]["categorical_columns"].append(uuid)

            if i == 0:
                existing_spec_dict["columns"][uuid] = {
                    "type": "categorical",
                    "paired_columns": uuid_columns[1:] + static_columns,
                    "uniques": num_existing_records,
                    "original_values": "random",
                    "cross_join_all_unique_values": False,
                    "miss_probability": 0,
                    "anonymising_set": reference_table
                }

            else:
                existing_spec_dict["columns"][uuid] = {
                    "type": "categorical",
                    "paired_columns": [uuid_columns[0]],
                    "uniques": num_existing_records,
                    "original_values": "See paired column",
                    "cross_join_all_unique_values": False,
                    "miss_probability": 0,
                    "anonymising_set": reference_table
                }

    for column in static_columns:
        if column in existing_spec_dict["columns"]:
            existing_spec_dict["columns"][column] = {
                "type": "categorical",
                "paired_columns": [uuid_columns[0]],
                "uniques": num_existing_records,
                "original_values": "See paired column",
                "cross_join_all_unique_values": False,
                "miss_probability": 0,
                "anonymising_set": reference_table
            }

    exhibit_data = xbt.Exhibit(command="fromspec", source=existing_spec_dict, output="dataframe")
    existing_data_df = exhibit_data.generate()
    logger.info(f"Generated {len(existing_data_df)} updated records for existing entities.")
    return existing_data_df, existing_spec_dict


# In[10]:


# updating already existing records
# drawing from reference table
# using anonymising set in categorical columns where you can provide a table to draw from
# unique identifier columns set as categorical columns with the anonymizing set as the reference table
# handle static columns by pairing with a uuid in reference
# update the rest of columns

def generate_existing_records_from_third_period(existing_spec_dict):
    existing_spec_dict["metadata"]["random_seed"] += 1  # Increment for each month
    existing_spec_dict["metadata"]["number_of_rows"] = num_existing_records  # Expected number of rows for new records

    for date_column in date_columns:
        if date_column in existing_spec_dict["columns"]:
            current_start_date = existing_spec_dict["columns"][date_column]["from"]
            current_end_date = existing_spec_dict["columns"][date_column]["to"]
            new_start_date, new_end_date = update_dates(current_start_date, current_end_date, period, length_of_period)
            existing_spec_dict["columns"][date_column]["from"] = new_start_date
            existing_spec_dict["columns"][date_column]["to"] = new_end_date

    exhibit_data = xbt.Exhibit(command="fromspec", source=existing_spec_dict, output="dataframe")
    existing_data_df = exhibit_data.generate()
    logger.info(f"Generated {len(existing_data_df)} updated records for existing entities.")
    return existing_data_df, existing_spec_dict


# In[11]:


# combining new and updated records

def combine_and_shuffle_records(new_data_df, existing_data_df):
    combined_df = pd.concat([new_data_df, existing_data_df], ignore_index=True)
    shuffled_df = shuffle(combined_df).reset_index(drop=True)
    logger.info(f"Combined and shuffled {len(shuffled_df)} records (New: {len(new_data_df)}, Existing: {len(existing_data_df)}).")
    return shuffled_df


# In[12]:


# Adding new records into the database

def insert_new_records_to_reference(new_data_df, exhibit_db_path):
    with sqlite3.connect(exhibit_db_path) as conn:
        new_data_df.to_sql(reference_table, conn, if_exists="append", index=False)
    logger.info(f"Inserted {len(new_data_df)} new records into the reference table.")


# In[13]:


# issues with column ordering when combining and adding
# column ordering to ensure match

def get_column_order_from_reference_table(exhibit_db_path, reference_table):
    with sqlite3.connect(exhibit_db_path) as conn:
        query = f"PRAGMA table_info({reference_table})"
        column_info = pd.read_sql(query, conn)
    return column_info['name'].tolist()


# In[14]:


def write_new_spec_to_yaml(spec_dict, dataset_num):
    """
    Writes the specification dictionary to a YAML file.

    Args:
    - spec_dict (dict): The specification dictionary to be written.
    - dataset_num (int): The dataset number for naming the YAML file.
    """
    yaml_file_name = f"new_specification_dataset_{dataset_num}.yaml"
    with open(yaml_file_name, 'w') as yaml_file:
       yaml.dump(spec_dict, yaml_file, sort_keys=False, width=1000)
    logger.info(f"Wrote new specification to {yaml_file_name}.")


# In[15]:


def write_existing_spec_to_yaml(spec_dict, dataset_num):
    """
    Writes the specification dictionary to a YAML file.

    Args:
    - spec_dict (dict): The specification dictionary to be written.
    - dataset_num (int): The dataset number for naming the YAML file.
    """
    yaml_file_name = f"exisiting_specification_dataset_{dataset_num}.yaml"
    with open(yaml_file_name, 'w') as yaml_file:
       yaml.dump(spec_dict, yaml_file, sort_keys=False, width=1000)
    logger.info(f"Wrote exisitng specification to {yaml_file_name}.")


# In[16]:


# User Inputs

user_inputs = load_user_inputs(input_file_path)

# Extract parameters from the user_inputs
exhibit_db_path = user_inputs["exhibit_db_path"] # Path to the Exhibit database
date_columns = user_inputs["date_columns"]  # List of date columns to be updated each month
static_columns = user_inputs["static_columns"]  # List of static columns to maintain from existing records
period = user_inputs["period"] # can be months, weeks or days
length_of_period = user_inputs["length_of_period"] # integer, for example every 1 month
num_datasets = user_inputs.get("num_datasets", 3) # integer, number of required datasets, default to 1 if not provided
fraction_of_new = user_inputs["fraction_of_new"]  # fraction, fraction of new records vs existing
fraction_of_new = Fraction(fraction_of_new)
linked_columns = user_inputs["linked_columns"]


# In[17]:


# defining arguements (to be refined)
spec_dict = load_yaml_to_spec_dict(spec_file_path)
row_count = spec_dict["metadata"]["number_of_rows"]  # Expected number of rows for new records will be derived from this
num_new_records = int(row_count * fraction_of_new)
num_existing_records = row_count - num_new_records
table_id = spec_dict["metadata"]["id"]
uuid_columns = spec_dict["metadata"]["uuid_columns"]
reference_table = f"temp_{table_id}_reference" # name of reference table 
primary_unique_identifier = uuid_columns[0]
logger.info(f"Primary Unique Identifier: {primary_unique_identifier}")


# In[18]:


# calling in order

# Main Loop for Monthly Generation
for dataset_num in range(1, num_datasets + 1):  
    logger.info(f"\n--- Generating Dataset {dataset_num} ---")
    
    if dataset_num == 1:
        new_data_df = generate_first_period(spec_dict)
        
        # Save the first dataset as CSV
        new_data_df.to_csv(f"dataset_{dataset_num}.csv", index=False)

        write_new_spec_to_yaml(spec_dict, dataset_num)
        
        # Initialize new_spec_dict and existing_spec_dict
        column_order = get_column_order_from_reference_table(exhibit_db_path, reference_table)
        new_spec_dict = copy.deepcopy(spec_dict) 
        existing_spec_dict = copy.deepcopy(spec_dict)

    elif dataset_num == 2:
        new_data_df, new_spec_dict = generate_new_records(new_spec_dict)

        # Generate existing records for this dataset (using the updated existing_spec_dict)
        existing_data_df, existing_spec_dict = generate_existing_records(existing_spec_dict)

        # Ensure the new and existing datasets have the correct column order
        new_data_df = new_data_df[column_order]
        existing_data_df = existing_data_df[column_order]

        # Combine and shuffle new and existing records
        final_dataset = combine_and_shuffle_records(new_data_df, existing_data_df)

        # Insert the new records into the reference table for future updates
        insert_new_records_to_reference(new_data_df, exhibit_db_path)

        # Save the final dataset to a CSV file
        final_dataset.to_csv(f"dataset_{dataset_num}.csv", index=False)
        # For subsequent datasets, we progressively modify new_spec_dict and existing_spec_dict

        write_new_spec_to_yaml(new_spec_dict, dataset_num)
        write_existing_spec_to_yaml(existing_spec_dict, dataset_num)
        
    else:
        new_data_df, new_spec_dict = generate_new_records(new_spec_dict)

        # Generate existing records for this dataset (using the updated existing_spec_dict)
        existing_data_df, existing_spec_dict = generate_existing_records_from_third_period(existing_spec_dict)

        # Ensure the new and existing datasets have the correct column order
        new_data_df = new_data_df[column_order]
        existing_data_df = existing_data_df[column_order]

        # Combine and shuffle new and existing records
        final_dataset = combine_and_shuffle_records(new_data_df, existing_data_df)

        # Insert the new records into the reference table for future updates
        insert_new_records_to_reference(new_data_df, exhibit_db_path)

        # Save the final dataset to a CSV file
        final_dataset.to_csv(f"dataset_{dataset_num}.csv", index=False)
        # For subsequent datasets, we progressively modify new_spec_dict and existing_spec_dict

        write_new_spec_to_yaml(new_spec_dict, dataset_num)
        write_existing_spec_to_yaml(existing_spec_dict, dataset_num)


# In[ ]:


# clean up the temp_tables
db_util.purge_temp_tables()


# In[ ]:




