import csv
import os

def write_error_to_csv(csv_dir, error_type, error_traceback, address):
    csv_file_path = os.path.join(csv_dir, "error_log.csv")
    with open(csv_file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([error_type, error_traceback, address])
        
def merge_error_logs(root_folder, output_file):
    with open(output_file, mode='a', newline='') as merged_file:
        writer = csv.writer(merged_file)

        for foldername, subfolders, filenames in os.walk(root_folder):
            for filename in filenames:
                if filename == 'error_log.csv':
                    filepath = os.path.join(foldername, filename)
                    with open(filepath, mode='r', newline='') as file:
                        reader = csv.reader(file)
                        for row in reader:
                            writer.writerow(row)
                            
if __name__ == "__main__":
    merge_error_logs()