# Series-Generation
The Series Generation tool is designed to generate a series of synthetic datasets over several periods using the Exhibit framework. The tool enables users to simulate periodic data, accounting for new entities and updates to existing entities.
# User provides:
Two YAML files:
  - Exhibit specification file with dates for first period
  - User input file describing:
     - path to exhibit db
     - date columns to be updated
     - static columns to be maintained for existing entities
     - The period of the series, can either be ‘months’, ‘weeks’ or ‘days’
     - The length of period, an integer
     - The number of datasets, an integer
     - The required fraction of new records vs existing records in each period
     - List of linked columns
# How to use:
Install exhibit
```pip install ehxibit```
Install Sklearn
```pip install scikit-learn```
Run the series generation tool, providing paths to the specification yaml and user_input yaml
```python Series_generation.py --specification example_spec.yml --user_input example_user_input.yml```

To use the example user_input yaml template:
  - add path to exhibit db
