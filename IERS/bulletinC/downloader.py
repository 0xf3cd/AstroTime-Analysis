import requests
from pathlib import Path

FIRST_FILE_NUMBER = 10
LAST_FILE_NUMBER = 68

# Create the folders to store the data
DATA_PATH = Path(__file__).parent / 'data'
assert not DATA_PATH.exists(), f'{DATA_PATH} already exists.'
DATA_PATH.mkdir()


# Download the files
error_file_names = []

for file_number in range(FIRST_FILE_NUMBER, LAST_FILE_NUMBER + 1):
  file_name = f'bulletinc-{file_number:03}.txt'
  file_url  = f'https://datacenter.iers.org/data/16/{file_name}'
  file_path = DATA_PATH / file_name
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
