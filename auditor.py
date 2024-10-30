import os
import sys
import yaml
import logging
import hashlib
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime


def setup_logging():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )


def load_config(config_path):
    try:
        with open(config_path, "r") as config_file:
            return yaml.safe_load(config_file)
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing configuration file: {e}")
        sys.exit(1)


def get_campaign_hash(row):
    """Create a unique identifier for each campaign based on key fields"""
    key_fields = [
        str(row["Tactic Order ID"]),
        str(row["Retailer"]),
        str(row["Tactic Brand"]),
        str(row["Event Name"]),
    ]
    return hashlib.md5("|".join(key_fields).encode()).hexdigest()


def load_historical_data(history_file):
    """Load the previous version of the campaign data"""
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                return pd.read_json(f)
        except Exception as e:
            logging.warning(f"Could not load historical data: {e}")
            return None
    return None


def save_historical_data(df, history_file):
    """Save the current version of the campaign data"""
    try:
        df.to_json(history_file)
    except Exception as e:
        logging.error(f"Could not save historical data: {e}")


def validate_file_path(file_path, file_type):
    path = Path(file_path)
    if not path.exists():
        logging.error(f"{file_type} file does not exist: {file_path}")
        return False
    if file_type == "CSV" and path.suffix.lower() != ".csv":
        logging.error(f"Invalid file format. Expected CSV, got: {path.suffix}")
        return False
    return True


def read_and_clean_data(file_path):
    """Read and clean the CSV data, ensuring all required fields are present and properly formatted"""
    logging.info(f"Reading data from {file_path}")
    if not validate_file_path(file_path, "CSV"):
        sys.exit(1)

    try:
        df = pd.read_csv(file_path)
    except pd.errors.EmptyDataError:
        logging.error("The CSV file is empty.")
        sys.exit(1)
    except pd.errors.ParserError:
        logging.error("Error parsing the CSV file. Please check the file format.")
        sys.exit(1)

    required_columns = [
        "Tactic Start Date",
        "Tactic End Date",
        "Tactic Vendor",
        "Retailer",
        "Tactic Brand",
        "Event Name",
        "Tactic Name",
        "Tactic Product",
        "Tactic Order ID",
        "Tactic Allocated Budget",
    ]

    # Check for missing columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logging.error(f"Missing required columns in CSV: {', '.join(missing_columns)}")
        sys.exit(1)

    # Remove summary rows and nulls
    df = df[df["Tactic Start Date"].notnull()]
    df = df[
        ~df["Tactic Start Date"]
        .astype(str)
        .str.contains("Grand Total|Total|Summary", na=False, case=False)
    ]

    # Convert dates
    for date_col in ["Tactic Start Date", "Tactic End Date"]:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # Remove rows with invalid dates
    df = df[df["Tactic Start Date"].notnull() & df["Tactic End Date"].notnull()]

    # Normalize dates to midnight
    df["Tactic Start Date"] = df["Tactic Start Date"].dt.normalize()
    df["Tactic End Date"] = df["Tactic End Date"].dt.normalize()

    # Convert budget to numeric, replacing any non-numeric values with 0
    df["Tactic Allocated Budget"] = pd.to_numeric(
        df["Tactic Allocated Budget"], errors="coerce"
    ).fillna(0)

    # Fill empty vendors with blank string instead of NaN
    df["Tactic Vendor"] = df["Tactic Vendor"].fillna("")

    # Sort by date for consistent ordering
    df = df.sort_values(["Tactic Start Date", "Retailer", "Tactic Brand"])

    logging.info(f"Successfully processed {len(df)} campaigns")
    return df


def categorize_campaigns(df):
    """Categorize campaigns into current, future, and past based on dates"""
    current_date = pd.Timestamp.now().normalize()

    # Current campaigns: Start date <= current date <= end date
    current_campaigns = df[
        (df["Tactic Start Date"] <= current_date)
        & (df["Tactic End Date"] >= current_date)
    ].copy()

    # Future campaigns: Start date > current date
    future_campaigns = df[df["Tactic Start Date"] > current_date].copy()

    # Past campaigns: End date < current date
    past_campaigns = df[df["Tactic End Date"] < current_date].copy()

    # Sort each category appropriately
    current_campaigns.sort_values(
        ["Tactic End Date", "Retailer", "Tactic Brand"], inplace=True
    )
    future_campaigns.sort_values(
        ["Tactic Start Date", "Retailer", "Tactic Brand"], inplace=True
    )
    past_campaigns.sort_values(
        ["Tactic End Date", "Retailer", "Tactic Brand"],
        ascending=[False, True, True],
        inplace=True,
    )

    return current_campaigns, future_campaigns, past_campaigns


def find_changes(current_df, historical_df):
    """Identify changes between current and historical data"""
    if historical_df is None:
        return current_df.assign(changes=[[] for _ in range(len(current_df))])

    # Add hash identifier to both dataframes
    current_df["hash"] = current_df.apply(get_campaign_hash, axis=1)
    historical_df["hash"] = historical_df.apply(get_campaign_hash, axis=1)

    # Fields to monitor for changes
    monitored_fields = [
        "Tactic Allocated Budget",
        "Tactic Start Date",
        "Tactic End Date",
        "Tactic Vendor",
        "Tactic Product",
    ]

    changes = []
    for _, current_row in current_df.iterrows():
        campaign_changes = []
        historical_row = historical_df[historical_df["hash"] == current_row["hash"]]

        if len(historical_row) == 0:
            campaign_changes.append("New Campaign")
        else:
            historical_row = historical_row.iloc[0]
            for field in monitored_fields:
                current_value = current_row[field]
                historical_value = historical_row[field]

                # Handle date comparisons
                if field in ["Tactic Start Date", "Tactic End Date"]:
                    current_value = pd.to_datetime(current_value)
                    historical_value = pd.to_datetime(historical_value)

                if current_value != historical_value:
                    if field == "Tactic Allocated Budget":
                        diff = current_value - historical_value
                        change_str = f"Budget changed from ${historical_value:,.2f} to ${current_value:,.2f} (${diff:+,.2f})"
                    elif field in ["Tactic Start Date", "Tactic End Date"]:
                        change_str = f"{field.replace('Tactic ', '')} changed from {historical_value.strftime('%Y-%m-%d')} to {current_value.strftime('%Y-%m-%d')}"
                    else:
                        change_str = f"{field.replace('Tactic ', '')} changed from '{historical_value}' to '{current_value}'"
                    campaign_changes.append(change_str)

        changes.append(campaign_changes)

    current_df["changes"] = changes
    return current_df


def write_campaign_details(md_file, campaign, indent_level=0):
    indent = "  " * indent_level
    start_date = pd.to_datetime(campaign["Tactic Start Date"]).strftime("%Y-%m-%d")
    end_date = pd.to_datetime(campaign["Tactic End Date"]).strftime("%Y-%m-%d")
    budget = campaign["Tactic Allocated Budget"]

    # Add a ⚠️ symbol if there are changes
    changes = campaign.get("changes", [])
    change_indicator = "⚠️ " if changes and changes != ["New Campaign"] else ""

    md_file.write(
        f"{indent}- **{change_indicator}{campaign['Retailer']}** - {campaign['Tactic Brand']}\n"
    )

    # If this is a new campaign, highlight it
    if changes and changes == ["New Campaign"]:
        md_file.write(f"{indent}  - 🆕 **New Campaign**\n")

    md_file.write(f"{indent}  - Event: {campaign['Event Name']}\n")
    md_file.write(f"{indent}  - Product: {campaign['Tactic Product']}\n")
    md_file.write(f"{indent}  - Campaign: {campaign['Tactic Name']}\n")
    if campaign["Tactic Vendor"]:
        md_file.write(f"{indent}  - Vendor: {campaign['Tactic Vendor']}\n")
    md_file.write(f"{indent}  - Dates: {start_date} to {end_date}\n")
    md_file.write(f"{indent}  - Budget: ${budget:,.2f}\n")
    md_file.write(f"{indent}  - Order ID: {campaign['Tactic Order ID']}\n")

    # List any changes detected
    if changes and changes != ["New Campaign"]:
        md_file.write(f"{indent}  - **Changes Detected:**\n")
        for change in changes:
            md_file.write(f"{indent}    - {change}\n")

    md_file.write(f"{indent}  - [ ] Campaign Setup Complete\n")
    md_file.write(f"{indent}  - [ ] Creative Assets Received\n")
    md_file.write(f"{indent}  - [ ] Campaign Launch Verified\n\n")


def write_campaign_section(md_file, campaigns, section_title):
    if not campaigns.empty:
        total_budget = campaigns["Tactic Allocated Budget"].sum()
        campaign_count = len(campaigns)

        # Count campaigns with changes
        changed_campaigns = len([c for c in campaigns["changes"] if c])
        change_indicator = (
            f" (🔄 {changed_campaigns} with changes)" if changed_campaigns else ""
        )

        md_file.write(
            f"# {section_title} ({campaign_count} Campaigns{change_indicator})\n"
        )
        md_file.write(f"**Total Budget: ${total_budget:,.2f}**\n\n")

        # Group by retailer for better organization
        for retailer in sorted(campaigns["Retailer"].unique()):
            retailer_campaigns = campaigns[campaigns["Retailer"] == retailer]
            retailer_budget = retailer_campaigns["Tactic Allocated Budget"].sum()

            md_file.write(f"## {retailer} (${retailer_budget:,.2f})\n\n")

            for _, campaign in retailer_campaigns.iterrows():
                write_campaign_details(md_file, campaign)

        md_file.write("---\n\n")
    else:
        md_file.write(f"# {section_title} (0 Campaigns)\n")
        md_file.write("*No campaigns in this category.*\n\n---\n\n")


def generate_checklist(df, history_file, output_path):
    logging.info(f"Generating checklist and saving to {output_path}")
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Load historical data and find changes
    historical_df = load_historical_data(history_file)
    df = find_changes(df, historical_df)

    # Save current data as historical
    save_historical_data(df, history_file)

    # Categorize campaigns
    current_campaigns, future_campaigns, past_campaigns = categorize_campaigns(df)

    with open(output_path, "w", encoding="utf-8") as md_file:
        md_file.write(f"# Campaign Status Report - Generated on {current_date}\n\n")

        # Summary section with change indicators
        total_budget = df["Tactic Allocated Budget"].sum()
        total_changes = len([c for c in df["changes"] if c])
        new_campaigns = len([c for c in df["changes"] if c == ["New Campaign"]])

        md_file.write(f"## Summary\n")
        if total_changes > 0:
            md_file.write(
                f"**🔄 Changes Detected: {total_changes} campaigns updated**\n"
            )
        if new_campaigns > 0:
            md_file.write(f"**🆕 New Campaigns: {new_campaigns}**\n")
        md_file.write(f"- Currently Active Campaigns: {len(current_campaigns)}\n")
        md_file.write(f"- Upcoming Campaigns: {len(future_campaigns)}\n")
        md_file.write(f"- Completed Campaigns: {len(past_campaigns)}\n")
        md_file.write(f"- Total Budget Across All Campaigns: ${total_budget:,.2f}\n\n")

        if total_changes > 0:
            md_file.write("### Change Indicators:\n")
            md_file.write("- ⚠️ Campaign has changes\n")
            md_file.write("- 🆕 New campaign\n")
            md_file.write("- 🔄 Number of changes in section\n\n")

        md_file.write("---\n\n")

        # Write each section
        write_campaign_section(md_file, current_campaigns, "Currently Active Campaigns")
        write_campaign_section(md_file, future_campaigns, "Upcoming Campaigns")
        write_campaign_section(md_file, past_campaigns, "Completed Campaigns")


def get_unique_filename(base_path):
    """Generate a unique filename by adding a sequence number if needed"""
    directory = os.path.dirname(base_path)
    base_name = os.path.splitext(os.path.basename(base_path))[0]
    extension = os.path.splitext(base_path)[1]

    counter = 1
    new_path = base_path

    while os.path.exists(new_path):
        timestamp = datetime.now().strftime("%H%M%S")
        new_name = f"{base_name}_{timestamp}_{counter}{extension}"
        new_path = os.path.join(directory, new_name)
        counter += 1

    return new_path


def save_historical_data(df, history_dir):
    """Save the current version of the campaign data with proper date handling"""
    os.makedirs(history_dir, exist_ok=True)

    # Create a copy for saving to avoid modifying the original
    df_to_save = df.copy()

    # Convert dates to ISO format strings for consistent serialization
    date_columns = ["Tactic Start Date", "Tactic End Date"]
    for col in date_columns:
        df_to_save[col] = df_to_save[col].dt.strftime("%Y-%m-%d")

    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_file = os.path.join(history_dir, f"campaign_history_{timestamp}.json")

    try:
        # Save with date formatting preserved
        df_to_save.to_json(history_file, orient="records", date_format="iso")
        logging.info(f"Historical data saved to {history_file}")

        # Update latest.json to point to most recent version
        latest_file = os.path.join(history_dir, "campaign_history_latest.json")
        df_to_save.to_json(latest_file, orient="records", date_format="iso")

        return history_file
    except Exception as e:
        logging.error(f"Could not save historical data: {e}")
        return None


def load_historical_data(history_dir):
    """Load the previous version of the campaign data with proper date parsing"""
    latest_file = os.path.join(history_dir, "campaign_history_latest.json")

    if not os.path.exists(latest_file):
        logging.info("No historical data found")
        return None

    try:
        # Load the data with proper date parsing
        df = pd.read_json(latest_file, orient="records")

        # Convert date strings back to datetime
        date_columns = ["Tactic Start Date", "Tactic End Date"]
        for col in date_columns:
            df[col] = pd.to_datetime(df[col])

        return df
    except Exception as e:
        logging.warning(f"Could not load historical data: {e}")
        return None


def main(config_path):
    setup_logging()
    config = load_config(config_path)
    df = read_and_clean_data(config["input_offsite_csv"])

    # Set up history directory instead of single file
    history_dir = os.path.join(config["output_dir"], "campaign_history")
    os.makedirs(history_dir, exist_ok=True)

    # Create base output filename
    base_output_name = f"Campaign_Status_Report_{datetime.now().strftime('%Y%m%d')}.md"
    base_output_path = os.path.join(config["output_dir"], base_output_name)

    # Get unique output path
    output_path = get_unique_filename(base_output_path)

    # Load historical data and generate report
    historical_df = load_historical_data(history_dir)
    df = find_changes(df, historical_df)

    # Save current data as new historical version
    save_historical_data(df, history_dir)

    generate_checklist(df, history_dir, output_path)
    print(f"Campaign status report generated and saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Campaign Status Report")
    parser.add_argument(
        "--config", type=str, default="config.yaml", help="Path to configuration file"
    )
    args = parser.parse_args()
    main(args.config)
