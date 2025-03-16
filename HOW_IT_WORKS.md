## Process

#### The process is divided into four main phases for each periodic batch:
1. Generating new records – achieved by changing random seed to ensure new entities with new unique identifiers and updating date columns to reflect current period. 
2. Updating existing records - by drawing existing entities from a reference table containing previous records, attributes that are unlikely to change are also drawn from the reference table, for example gender or country of birth, these are maintained throughout the series generation, while attributes that can be updated are generated a fresh with a new random seed to simulate changes, for example consent, class year, and their unique identifiers always remain the same.
3. After each period’s generation, new records are added to the reference table to be used for subsequent periods.
4. New and existing records are combined, and saved together with respective YAML spec. 
## How this is achieved
Load YAML Specification and User Input
The tool accepts, two YAML files:
1.	Exhibit specification YAML
-	This will be details of all the required columns, with dates set to initial period of generation. Entities to be generated must have unique identifiers.
2.	User Input YAML
This is a provided template, where user fills in:
- Path to the Exhibit database
- List of date columns to be updated in each period
- List of static columns to be maintained from previous records
- The period of the series, can either be ‘months’, ‘weeks’ or ‘days’
- The length of period, an integer
- The number of datasets, an integer
- The required fraction of new records vs existing records in each period
- Linked columns
###### Examples:
- A series of 5 datasets generated every 2 weeks with ½ new records for every period
- A series of 10 datasets generated every 1 month with 1/3 new records for every period
##### Generation:
##### The first part loads the YAML files as dictionaries. 
- To generate the first period, the specification dictionary is passed into exhibit as is. The generated records are then inserted into the local exhibit database. 
- To generate subsequent periods, original specification dictionary is modified.
- To generate new records, the specification dictionary is modified by changing the random seed, this is 1 increment from the original seed. The number of rows for new records is calculated from the user provided fraction of new vs existing:
```
Number_of_records = fraction of (number_of_rows in original spec)
```
- User provides dates to be updated in each period, the tool loops over the list provided and modifies the spec dictionary to the reflect the current period. This is done by incrementing the ‘from’ and ‘to’ dates by user provided length of period and period. 
###### Example:
```
Original_Spec[columns][date][from] = 01/01/2024
1 month increment:
Modified_spec[columns][date][from] = 01/02/2024
```
The modified specification is run with exhibit to generate new records with new unique identifiers and present dates.
- To update existing records, the original specification dictionary is modified.
- Instead of generating unique identifiers, for existing records, ids are drawn from the previously saved reference table. This done by converting id columns in the spec dictionary into categorical columns, where the anonymizing set is the reference table.
##### Example:
Original spec:
```
columns:
  id:
    type: uuid
    uuid_seed: 0
    frequency_distribution:
    - frequency | probability_vector
    - 1        	 | 1.0
    miss_probability: 0.0
    anonymising_set: uuid	
Modified spec:
	columns:
	  id:
          type: categorical,
          paired_columns: uuid_columns[1:] + static_columns,
          uniques: num_existing_records,
          original_values: random,
          cross_join_all_unique_values: False,
          miss_probability: 0,
          anonymising_set: reference_table  	
```

All unique identifiers are converted to categorical columns in this way. They are also all paired with static columns in the reference table. These are columns the user wishes to maintain when updating existing records. For example, if an id was recorded as female in previous records and the user would like to maintain gender in updates, gender is paired with unique ids and drawn from the reference table as previously saved.

``` 
Original spec:
Columns
gender:
    type: categorical
    original_values:
    - gender	    | probability_vector |
    - F                        | 0.5                                 |
    - M                       | 0.5	                               |
    - Missing data | 0.000                           |
    paired_columns:
    uniques: 2
    cross_join_all_unique_values: false
    miss_probability: 0.0
    anonymising_set: random
    dispersion: 0

Modified spec:
Columns
gender:
    type: categorical
    original_values: See paired column
    paired_columns: [uuid_columns[0]]
    uniques: num_existing_records
    cross_join_all_unique_values: false
    miss_probability: 0.0
    anonymising_set: reference_table
    dispersion: 0
```

Therefore, for existing records drawn from the reference table, the updated dates and maintained columns cannot have constraints or derivations. For example, if date created is to be maintained in updated records, and date valid from is updated in every period, existing records cannot have a constraint such as:

```
constraints:
  allow_duplicates: false
  basic_constraints:
    - date_updated == date_created
    - date_valid_from == date_updated
  custom_constraints:
```

The tool handles this by removing constraints and derivatives that mention these forbidden values (dates to be updated, and static columns to maintain). The modified spec is saved and run with exhibit.

The resulting data frames for new records and existing records are shuffled and combined into a csv file, saved as dataset_1, dataset_2 and so on. New records are added into the reference table and the next period generated in the same way using the modified specifications, so that when the dates are updated, it goes onto the next period.

##### Required Libraries
The tool uses the following Python libraries:
- pandas
- exhibit
- yaml
- sklearn.utils
- copy
- datetime
- dateutil.relativedelta
- sqlite3
