import os

def test_file_exists():
    file_path = os.path.join('data', 'raw', 'gemeenten-alfabetisch-2024.xlsx')
    exists = os.path.exists(file_path)
    print(f"Looking for file at: {os.path.abspath(file_path)}")
    print(f"File exists: {exists}")
    return exists

if __name__ == "__main__":
    test_file_exists()
    