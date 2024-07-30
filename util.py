import json

def sats_per_kb_to_sats_per_byte(sats_per_kb):
    """
    Converts satoshis per kilobyte to satoshis per byte.

    Parameters:
    sats_per_kb (float): Fee rate in satoshis per kilobyte.

    Returns:
    int: Fee rate in satoshis per byte.
    """
    return int(float(sats_per_kb) / 1000)

def read_and_process_file(file_path, read_function):
    """
    Reads a JSON file and processes its content using a specified function.

    Parameters:
    file_path (str): The path to the JSON file.
    read_function (function): The function to process the JSON content.

    Returns:
    list: Processed data or an empty list if an error occurs.
    """
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
        return read_function(data)
    except (IOError, ValueError) as e:
        print(f"Error reading or processing file {file_path}: {e}")
        return []

def read_fees(estimates_dict):
    """
    Processes fee estimates data.

    Parameters:
    estimates_dict (list): List of dictionaries containing fee estimates.

    Returns:
    list: Filtered fee estimates.
    """
    return [
        {
            "conf_target": int(float(estimate["conf_target"])),
            "block_height": int(float(estimate["block_height"])),
            "conservative_fee_rate": sats_per_kb_to_sats_per_byte(estimate["conservative_fee_rate"]),
            "economic_fee_rate": sats_per_kb_to_sats_per_byte(estimate["economic_fee_rate"]),
        }
        for estimate in estimates_dict
    ]

def read_blocks(blocks_dict):
    """
    Processes block data.

    Parameters:
    blocks_dict (list): List of dictionaries containing block data.

    Returns:
    dict: Filtered block data.
    """
    filtered_blocks = {}
    for block in blocks_dict:
        try:
            height = int(float(block["block_height"]))
            filtered_block = {
                "conf_height": int(float(block["block_height"])),
                "p_5": sats_per_kb_to_sats_per_byte(block["p_5"]),
                "p_50": sats_per_kb_to_sats_per_byte(block["p_50"])
            }
            filtered_blocks[height] = filtered_block
        except (ValueError, KeyError) as e:
            print(f"Error processing block data: {e}")
    return filtered_blocks



def read_data_from_file(fees_file_path=None, blocks_file_path=None):
    """
    Reads and processes data from JSON files.

    Parameters:
    fees_file_path (str): The path to the fees JSON file.
    blocks_file_path (str): The path to the blocks JSON file.

    Returns:
    tuple: A tuple containing processed fee estimates and block data.
    """
    fees_data = read_and_process_file(fees_file_path, read_fees) if fees_file_path else []
    blocks_data = read_and_process_file(blocks_file_path, read_blocks) if blocks_file_path else []
    return fees_data, blocks_data

def sanity_check_data(estimates, maximum_block_height):
    minimum = maximum_block_height - 1008
    while len(estimates) > 0 and minimum < estimates[-1]["block_height"]:
        estimates.pop()
    return estimates

def calculate_percentages(estimates, blocks):
    """
    Calculates the percentages of underpaid, overpaid, and within-range estimates.

    Parameters:
    estimates (list): List of fee estimates.
    blocks (dict): Dictionary of block data.

    Returns:
    tuple: A tuple containing the results for conservative and economic modes.
    """
    cons_result = {}
    econs_result = {}

    def initialize_results():
        return {"underpaid": 0, "overpaid": 0, "within the range": 0}

    def update_results(res, target, result_dict):
        if res[1]:
            result_dict[target]["overpaid"] += 1
        elif res[2]:
            result_dict[target]["within the range"] += 1
        else:
            result_dict[target]["underpaid"] += 1

    for estimate in estimates:
        cons_res = [False, False, False]  # "underpaid", "overpaid", "within the range"
        econs_res = [False, False, False]  # "underpaid", "overpaid", "within the range"
        curr_height = estimate["block_height"]
        conf_target = estimate["conf_target"]
        max_height = curr_height + conf_target
        curr_height += 1

        if conf_target not in cons_result:
            cons_result[conf_target] = initialize_results()
        if conf_target not in econs_result:
            econs_result[conf_target] = initialize_results()

        while curr_height < max_height:
            if curr_height not in blocks:
                curr_height += 1
                continue
            block = blocks[curr_height]
            if estimate["conservative_fee_rate"] < block["p_5"]:
                cons_res[0] = True
            if estimate["conservative_fee_rate"] > block["p_50"]:
                cons_res[1] = True
            else:
                cons_res[2] = True

            if estimate["economic_fee_rate"] < block["p_5"]:
                econs_res[0] = True
            if estimate["economic_fee_rate"] > block["p_50"]:
                econs_res[1] = True
            else:
                econs_res[2] = True
            curr_height += 1

        update_results(cons_res, conf_target, cons_result)
        update_results(econs_res, conf_target, econs_result)

    total = len(estimates) / 12

    def calculate_percentage(results):
        for target in results:
            for key in ["underpaid", "overpaid", "within the range"]:
                results[target][f"{key} perc"] = (results[target][key] / total) * 100

    calculate_percentage(cons_result)
    calculate_percentage(econs_result)

    return cons_result, econs_result

def print_summary(results, mode):
    """
    Prints a summary of the results.

    Parameters:
    results (dict): Dictionary of results.
    mode (str): Mode of fee estimation ("conservative" or "economic").
    """
    for target, result in results.items():
        print(f"Conf target: {target}")
        for category in ["underpaid", "overpaid", "within the range"]:
            count = result[category]
            percentage = result[f"{category} perc"]
            print(f"{count} estimates {category} ({percentage:.2f}% of the total estimates) in {mode} mode")
        print("---------------------------------------------------------")

def get_summary(data):
    """
    Generates a summary of the data.

    Parameters:
    data (tuple): Tuple containing estimates data and block data.
    """
    estimates_data = data[0]
    block_data = data[1]
    maximum_block_height = max(list(block_data.keys()))
    estimates_data = sanity_check_data(estimates_data, maximum_block_height)

    total = len(estimates_data)
    start_block = estimates_data[0]['block_height'] - 1
    end_block = estimates_data[-1]['block_height'] - 1

    print(f"Total of {total} estimates were made from Block {start_block} to Block {end_block}")
    print("---------------------------------------------------------")

    cons_result, econs_result = calculate_percentages(estimates_data, block_data)
    print_summary(cons_result, "conservative")
    print_summary(econs_result, "economic")