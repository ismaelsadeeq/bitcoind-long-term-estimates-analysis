from util import read_data_from_file, get_summary

fees_file_name = "forecast_longterm.json"
blocks_file_name = "longterm_blocks.json"

data = read_data_from_file(fees_file_path=fees_file_name, blocks_file_path=blocks_file_name)

if __name__ == "__main__":
    get_summary(data)
