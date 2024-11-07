import csv
from datetime import datetime

def parse_csv(file_path):
    """Helper function to read CSV file and return data."""
    with open(file_path, mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)

def generate_nacha_file(amounts_csv, banks_csv, output_file):
    """Generate NACHA file using data from two CSV files."""

    # Initialize batch count
    batch_count = 1

    # Load data from CSV files
    amounts_data = parse_csv(amounts_csv)
    banks_data = parse_csv(banks_csv)

    if not amounts_data or not banks_data:
        raise ValueError("One or both CSV files are empty or invalid.")

    # ===========================
    # File Header
    # 
    # Format reference: https://achdevguide.nacha.org/ach-file-details
    # ===========================
    now = datetime.now()
    file_creation_date = now.strftime("%y%m%d")
    file_creation_time = now.strftime("%H%M")
    immediate_dest = "123456789"
    immediate_org = "123456789"
    file_id_modifier = "A"
    record_size = "094"
    blocking_factor = "10"
    format_code = "1"
    immediate_dest_name = "SomeBankName".ljust(23)
    immediate_org_name = "MyCompany".ljust(23)
    reference_code = " ".ljust(8)

    file_header = (
        f"101 {immediate_dest} {immediate_org}{file_creation_date}{file_creation_time}"
        f"{file_id_modifier}{record_size}{blocking_factor}{format_code}"
        f"{immediate_dest_name}{immediate_org_name}{reference_code}\n"
    ).ljust(94)

    #print(file_creation_date)
    #print(file_creation_time)

    # ============================
    # Batch Header
    # ============================
    service_class_code = "220"
    company_name = "My Company".ljust(16)

    # still occupies space regardless its optional
    company_discretionary_data = ""
    company_discretionary_data_padded = company_discretionary_data.ljust(20)

    company_id = "123456789".ljust(10)    
    entry_descr = "PMT".ljust(10)
    descriptive_date = file_creation_date
    effective_entry_date = file_creation_date

    # Settlement date (Julian) - Reserved. Fill with spaces
    settlement_date = ""
    settlement_date_padded = settlement_date.ljust(3)

    originating_dfi = immediate_dest[:8]
    initial_batch_num = batch_num = 1

    batch_header = (
            f"5{service_class_code}{company_name}{company_discretionary_data_padded}{company_id}PPD{entry_descr}{descriptive_date}{effective_entry_date}{settlement_date_padded}1{originating_dfi}"
            f"{str(initial_batch_num).zfill(7)}\n"
    ).ljust(94)

    # Entry Detail Records
    entry_details = ""
    entry_hash = 0
    total_debit = 0
    total_credit = 0
    entry_count = 0

    for bank, amount in zip(banks_data, amounts_data):
        receiving_dfi = bank["Receiving DFI"].strip()[:8].ljust(8)
        check_digit = bank["Receiving DFI"].strip()[-1] # Get the last digit
        account_number = bank["Account Number"].strip()[:17].rjust(17)
        individual_id = bank["Individual ID"].strip()[:15].ljust(15)
        individual_name = bank["Individual Name"].strip()[:22].ljust(22)
        transaction_code = "22"
        discretionary_data = "R".ljust(2)

        # Increment the batch no. for each entry
        trace_number = f"{immediate_dest[:8]}{str(batch_num).zfill(7)}"
        batch_num += 1

        # Entry amount in cents
        amount_in_cents = int(float(amount["Amount"]) * 100)

        # Determine total credits/debits
        total_credit += amount_in_cents if amount_in_cents > 0 else 0
        total_debit += abs(amount_in_cents) if amount_in_cents < 0 else 0

        # Add receiving DFI to entry hash
        entry_hash += int(receiving_dfi[:8])
        entry_count += 1

        entry_details += (
            f"6{transaction_code}{receiving_dfi}{check_digit}{account_number}{amount_in_cents:010}"
            f"{individual_id}{individual_name}{discretionary_data}0{trace_number}\n"
        ).ljust(94)

    # =======================
    # Batch Control
    # =======================
    bc_addenda_count = str(entry_count).zfill(6)
    entry_hash_str = str(entry_hash)[:10].rjust(10, '0')
    total_debit_str = f"{total_debit:012}"
    total_credit_str = f"{total_credit:012}"
    batch_num_padded = str(batch_num).zfill(7)

    # Message authentication code. If not used, fill with spaces.
    bc_message_auth_code = ""
    bc_message_auth_code_padded = bc_message_auth_code.ljust(19)

    batch_control = (
        f"8{service_class_code}{bc_addenda_count}{entry_hash_str}{total_debit_str}{total_credit_str}{company_id}{bc_message_auth_code_padded}"
        f"{''.ljust(6)}" # reserved
        f"{originating_dfi}{str(initial_batch_num).zfill(7)}\n"
    ).ljust(94)


    # ======================
    # File Control
    # ======================
    block_count = ((entry_count + 4) // 10) + 1  # 10 entries per block
    fc_entry_addenda_count = str(entry_count).zfill(8)

    file_control = (
        f"9{str(batch_count).zfill(6)}{str(block_count).rjust(6, '0')}{fc_entry_addenda_count}{entry_hash_str}{total_debit_str}{total_credit_str}"
        f"{''.ljust(39)}\n" # reserved
    ).ljust(94)

    # Generate NACHA file content
    nacha_content = file_header + batch_header + entry_details + batch_control + file_control

    # Write to output NACHA file
    with open(output_file, 'w') as file:
        file.write(nacha_content)

    print(f"NACHA file '{output_file}' has been generated successfully.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate NACHA file from CSV files.")
    parser.add_argument("amounts_csv", help="Path to the CSV file with total dollar amounts.")
    parser.add_argument("banks_csv", help="Path to the CSV file with bank information.")
    parser.add_argument("output_file", help="Path to save the generated NACHA file.")

    args = parser.parse_args()
    generate_nacha_file(args.amounts_csv, args.banks_csv, args.output_file)

