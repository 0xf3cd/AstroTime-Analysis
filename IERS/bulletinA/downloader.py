import requests
from pathlib import Path

FILE_METADATA = {
  'xviii':  (2005, 52), # Year 2005
  'xix':    (2006, 52), # Year 2006
  'xx':     (2007, 52), # Year 2007
  'xxi':    (2008, 53), # Year 2008
  'xxii':   (2009, 52), # Year 2009
  'xxiii':  (2010, 52), # Year 2010
  'xxiv':   (2011, 52), # Year 2011
  'xxv':    (2012, 52), # Year 2012
  'xxvi':   (2013, 52), # Year 2013
  'xxvii':  (2014, 52), # Year 2014
  'xxviii': (2015, 53), # Year 2015
  'xxix':   (2016, 52), # Year 2016
  'xxx':    (2017, 52), # Year 2017
  'xxxi':   (2018, 52), # Year 2018
  'xxxii':  (2019, 52), # Year 2019
  'xxxiii': (2020, 53), # Year 2020
  'xxxiv':  (2021, 52), # Year 2021
  'xxxv':   (2022, 52), # Year 2022
  'xxxvi':  (2023, 52), # Year 2023
  'xxxvii': (2024, 27), # Year 2024 # As of now, only 27 files are available for 2024.
}

# Create the folders to store the data
DATA_PATH = Path(__file__).parent / 'data'
assert not DATA_PATH.exists(), f'{DATA_PATH} already exists.'
DATA_PATH.mkdir()

for year, _ in FILE_METADATA.values():
  YEAR_DATA_PATH = DATA_PATH / str(year)
  assert not YEAR_DATA_PATH.exists(), f'{YEAR_DATA_PATH} already exists.'
  YEAR_DATA_PATH.mkdir()


# Download the files
error_file_names = []

for year_roman, (year, file_count) in FILE_METADATA.items():
  for file_number in range(1, file_count + 1):
    file_name = f'bulletina-{year_roman}-{file_number:03}.txt'
    file_url  = f'https://datacenter.iers.org/data/6/{file_name}'
    file_path = DATA_PATH / str(year) / file_name
    assert not file_path.exists(), f'{file_path} already exists.'

    try:
      response = requests.get(file_url)
      response.raise_for_status()
      
      with open(file_path, 'wb') as f:
        f.write(response.content)

      print(f'Downloaded {file_name}')

    except Exception as e:
      error_file_names.append(file_name)
      print(f'Error downloading {file_name}: {e}')

print('-' * 60)
print(f'Error(s) occurred while downloading files: {error_file_names}')
