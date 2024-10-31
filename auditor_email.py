"""
Campaign Report Generator

Generates formatted Markdown and Text reports for tracking media campaign status across different retailers.
Tracks changes between report generations and maintains historical data for comparison.
"""

import os
import sys
import yaml
import logging
import hashlib
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Any
from dataclasses import dataclass

import smtplib
import logging
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
REQUIRED_COLUMNS = [
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

MONITORED_FIELDS = [
    "Tactic Allocated Budget",
    "Tactic Start Date",
    "Tactic End Date",
    "Tactic Vendor",
    "Tactic Product",
]

DATE_COLUMNS = ["Tactic Start Date", "Tactic End Date"]


# Custom Exceptions
class CampaignReportError(Exception):
    """Base exception for campaign report generation errors"""

    pass


class DataValidationError(CampaignReportError):
    """Raised when data validation fails"""

    pass


class HistoricalDataError(CampaignReportError):
    """Raised when handling historical data fails"""

    pass


@dataclass
class EmailConfig:
    """Configuration for email sending"""

    smtp_server: str = "smtp.office365.com"
    smtp_port: int = 587
    sender_email: str = None
    primary_recipients: List[str] = None
    cc_recipients: List[str] = None

    @classmethod
    def from_env(cls) -> "EmailConfig":
        """Create EmailConfig from environment variables"""
        # Load recipients from environment variables
        primary_recipients = os.getenv("EMAIL_PRIMARY_RECIPIENTS", "").split(",")
        cc_recipients = os.getenv("EMAIL_CC_RECIPIENTS", "").split(",")

        # Clean up recipient lists
        primary_recipients = [
            email.strip() for email in primary_recipients if email.strip()
        ]
        cc_recipients = [email.strip() for email in cc_recipients if email.strip()]

        return cls(
            smtp_server=os.getenv("EMAIL_SMTP_SERVER", "smtp.office365.com"),
            smtp_port=int(os.getenv("EMAIL_SMTP_PORT", "587")),
            sender_email=os.getenv("EMAIL_SENDER"),
            primary_recipients=primary_recipients,
            cc_recipients=cc_recipients,
        )

    def validate(self) -> bool:
        """Validate that required configuration is present"""
        if not self.sender_email:
            logging.error("Sender email not configured")
            return False
        if not self.primary_recipients:
            logging.error("No primary recipients configured")
            return False
        return True


class CampaignReportEmailer:
    """Handles sending campaign reports via email"""

    def __init__(self, config: EmailConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Get password from environment
        self.sender_password = os.getenv("EMAIL_SENDER_PASSWORD")
        if not self.sender_password:
            raise ValueError("Email sender password not found in environment variables")

    def setup_email_client(self) -> smtplib.SMTP:
        """Initialize and authenticate SMTP client"""
        try:
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
            server.starttls()
            server.login(self.config.sender_email, self.sender_password)
            return server
        except Exception as e:
            self.logger.error(f"Failed to setup email client: {e}")
            raise

    def create_email_message(
        self,
        subject: str,
        email_body: str,
        md_file_path: Optional[Path] = None,
        txt_file_path: Optional[Path] = None,
    ) -> MIMEMultipart:
        """Create email message with optional attachments"""
        msg = MIMEMultipart()
        msg["From"] = self.config.sender_email
        msg["To"] = ", ".join(self.config.primary_recipients)

        if self.config.cc_recipients:
            msg["CC"] = ", ".join(self.config.cc_recipients)

        msg["Subject"] = subject

        # Attach email body
        msg.attach(MIMEText(email_body, "plain"))

        # Attach files if provided
        for file_path in [p for p in [md_file_path, txt_file_path] if p]:
            if file_path.exists():
                with open(file_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename= {file_path.name}",
                    )
                    msg.attach(part)

        return msg

    def send_campaign_report(
        self, md_file_path: Path, txt_file_path: Path, report_date: str
    ) -> bool:
        """Send campaign report email with both markdown and text versions"""
        if not self.config.validate():
            self.logger.error("Invalid email configuration")
            return False

        try:
            # Read the text report content to use as email body
            with open(txt_file_path, "r", encoding="utf-8") as f:
                email_body = f.read()

            # Create email subject
            subject = f"Campaign Status Report - {report_date}"

            # Setup email server
            server = self.setup_email_client()

            # Create message
            msg = self.create_email_message(
                subject=subject,
                email_body=email_body,
                md_file_path=md_file_path,
                txt_file_path=None,  # Don't attach txt version since it's in the body
            )

            # Get all recipients
            all_recipients = self.config.primary_recipients + self.config.cc_recipients

            # Send email
            server.sendmail(self.config.sender_email, all_recipients, msg.as_string())

            server.quit()
            self.logger.info(
                f"Campaign report email sent successfully to {', '.join(all_recipients)}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to send campaign report email: {e}")
            return False


@dataclass
class Config:
    """Configuration container for the report generator"""

    input_csv: Path
    output_dir: Path
    email_template: Optional[str] = None

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """Create Config instance from YAML file"""
        try:
            with open(path) as f:
                data = yaml.safe_load(f)

            if not all(key in data for key in ["input_offsite_csv", "output_dir"]):
                raise DataValidationError("Missing required configuration keys")

            return cls(
                input_csv=Path(data["input_offsite_csv"]),
                output_dir=Path(data["output_dir"]),
                email_template=data.get("email_template"),
            )
        except (yaml.YAMLError, IOError) as e:
            raise DataValidationError(f"Failed to load configuration: {e}")


def setup_logging() -> None:
    """Configure logging format and level"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )


def get_campaign_hash(row: pd.Series) -> str:
    """
    Create a unique identifier for each campaign based on key fields

    Args:
        row: DataFrame row containing campaign data

    Returns:
        str: MD5 hash of concatenated key fields
    """
    key_fields = [
        str(row["Tactic Order ID"]),
        str(row["Retailer"]),
        str(row["Tactic Brand"]),
        str(row["Event Name"]),
    ]
    return hashlib.md5("|".join(key_fields).encode()).hexdigest()


def validate_file_path(path: Path, file_type: str) -> bool:
    """
    Validate that file exists and has correct extension

    Args:
        path: Path to file
        file_type: Expected file type (e.g., 'CSV')

    Returns:
        bool: True if file is valid
    """
    if not path.exists():
        logging.error(f"{file_type} file does not exist: {path}")
        return False
    if file_type == "CSV" and path.suffix.lower() != ".csv":
        logging.error(f"Invalid file format. Expected CSV, got: {path.suffix}")
        return False
    return True


def format_budget(amount: float) -> str:
    """Format budget amount with currency symbol and thousands separator"""
    return f"${amount:,.2f}"


def format_date(date: datetime) -> str:
    """Format date in consistent format"""
    return date.strftime("%Y-%m-%d")


def format_campaign_for_email(campaign: pd.Series, indent_level: int = 0) -> str:
    """Format campaign details for email output"""
    indent = "  " * indent_level
    start_date = format_date(pd.to_datetime(campaign["Tactic Start Date"]))
    end_date = format_date(pd.to_datetime(campaign["Tactic End Date"]))
    budget = campaign["Tactic Allocated Budget"]

    changes = campaign.get("changes", [])
    change_indicator = "[UPDATED] " if changes and changes != ["New Campaign"] else ""
    new_indicator = "[NEW] " if changes and changes == ["New Campaign"] else ""

    lines = [
        f"{indent}{change_indicator}{new_indicator}{campaign['Retailer']} - {campaign['Tactic Brand']}",
        f"{indent}Event: {campaign['Event Name']}",
        f"{indent}Product: {campaign['Tactic Product']}",
        f"{indent}Campaign: {campaign['Tactic Name']}",
    ]

    if campaign["Tactic Vendor"]:
        lines.append(f"{indent}Vendor: {campaign['Tactic Vendor']}")

    lines.extend(
        [
            f"{indent}Dates: {start_date} to {end_date}",
            f"{indent}Budget: {format_budget(budget)}",
            f"{indent}Order ID: {campaign['Tactic Order ID']}",
        ]
    )

    if changes and changes != ["New Campaign"]:
        lines.append(f"{indent}Changes:")
        for change in changes:
            lines.append(f"{indent}  * {change}")

    lines.append("")  # Add blank line
    return "\n".join(lines)


def read_and_clean_data(file_path: Path) -> pd.DataFrame:
    """
    Read and clean the CSV data, ensuring all required fields are present and properly formatted

    Args:
        file_path: Path to input CSV file

    Returns:
        DataFrame: Cleaned and validated campaign data

    Raises:
        DataValidationError: If data validation fails
    """
    logging.info(f"Reading data from {file_path}")
    if not validate_file_path(file_path, "CSV"):
        raise DataValidationError(f"Invalid file path: {file_path}")

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        raise DataValidationError(f"Failed to read CSV file: {e}")

    # Validate required columns
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise DataValidationError(f"Missing required columns: {missing_columns}")

    # Clean data
    df = df[df["Tactic Start Date"].notnull()]
    df = df[
        ~df["Tactic Start Date"]
        .astype(str)
        .str.contains("Grand Total|Total|Summary", na=False, case=False)
    ]

    # Convert dates
    for date_col in DATE_COLUMNS:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # Remove invalid dates
    df = df[df["Tactic Start Date"].notnull() & df["Tactic End Date"].notnull()]

    # Normalize dates and budget
    df["Tactic Start Date"] = df["Tactic Start Date"].dt.normalize()
    df["Tactic End Date"] = df["Tactic End Date"].dt.normalize()
    df["Tactic Allocated Budget"] = pd.to_numeric(
        df["Tactic Allocated Budget"], errors="coerce"
    ).fillna(0)
    df["Tactic Vendor"] = df["Tactic Vendor"].fillna("")

    # Sort for consistency
    df = df.sort_values(["Tactic Start Date", "Retailer", "Tactic Brand"])

    logging.info(f"Successfully processed {len(df)} campaigns")
    return df


def load_historical_data(history_dir: Path) -> Optional[pd.DataFrame]:
    """
    Load the previous version of the campaign data

    Args:
        history_dir: Directory containing historical data

    Returns:
        Optional[DataFrame]: Historical campaign data if available
    """
    latest_file = history_dir / "campaign_history_latest.json"

    if not latest_file.exists():
        logging.info("No historical data found")
        return None

    try:
        df = pd.read_json(latest_file, orient="records")
        for col in DATE_COLUMNS:
            df[col] = pd.to_datetime(df[col])
        return df
    except Exception as e:
        logging.warning(f"Could not load historical data: {e}")
        return None


def save_historical_data(df: pd.DataFrame, history_dir: Path) -> Optional[Path]:
    """
    Save the current version of the campaign data

    Args:
        df: Current campaign data
        history_dir: Directory to save historical data

    Returns:
        Optional[Path]: Path to saved history file
    """
    history_dir.mkdir(exist_ok=True)

    df_to_save = df.copy()
    for col in DATE_COLUMNS:
        df_to_save[col] = df_to_save[col].dt.strftime("%Y-%m-%d")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_file = history_dir / f"campaign_history_{timestamp}.json"
    latest_file = history_dir / "campaign_history_latest.json"

    try:
        df_to_save.to_json(history_file, orient="records", date_format="iso")
        df_to_save.to_json(latest_file, orient="records", date_format="iso")
        logging.info(f"Historical data saved to {history_file}")
        return history_file
    except Exception as e:
        logging.error(f"Could not save historical data: {e}")
        return None


def find_changes(
    current_df: pd.DataFrame, historical_df: Optional[pd.DataFrame]
) -> pd.DataFrame:
    """
    Identify changes between current and historical campaign data

    Args:
        current_df: Current campaign data
        historical_df: Historical campaign data

    Returns:
        DataFrame: Current data with added change information
    """
    if historical_df is None:
        return current_df.assign(changes=[[] for _ in range(len(current_df))])

    current_df["hash"] = current_df.apply(get_campaign_hash, axis=1)
    historical_df["hash"] = historical_df.apply(get_campaign_hash, axis=1)

    changes = []
    for _, current_row in current_df.iterrows():
        campaign_changes = []
        historical_row = historical_df[historical_df["hash"] == current_row["hash"]]

        if len(historical_row) == 0:
            campaign_changes.append("New Campaign")
        else:
            historical_row = historical_row.iloc[0]
            for field in MONITORED_FIELDS:
                current_value = current_row[field]
                historical_value = historical_row[field]

                if field in DATE_COLUMNS:
                    current_value = pd.to_datetime(current_value)
                    historical_value = pd.to_datetime(historical_value)

                if current_value != historical_value:
                    if field == "Tactic Allocated Budget":
                        diff = current_value - historical_value
                        change_str = (
                            f"Budget changed from {format_budget(historical_value)} "
                            f"to {format_budget(current_value)} "
                            f"({format_budget(diff) if diff >= 0 else f'-{format_budget(abs(diff))}'})"
                        )
                    elif field in DATE_COLUMNS:
                        change_str = (
                            f"{field.replace('Tactic ', '')} changed from "
                            f"{format_date(historical_value)} to {format_date(current_value)}"
                        )
                    else:
                        change_str = f"{field.replace('Tactic ', '')} changed from '{historical_value}' to '{current_value}'"
                    campaign_changes.append(change_str)

        changes.append(campaign_changes)

    current_df["changes"] = changes
    return current_df


def categorize_campaigns(
    df: pd.DataFrame, current_date: Optional[datetime] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Categorize campaigns into current, future, and past based on dates

    Args:
        df: Campaign data
        current_date: Date to use for categorization (default: current date)

    Returns:
        Tuple containing current, future, and past campaign DataFrames
    """
    if current_date is None:
        current_date = pd.Timestamp.now().normalize()

    current_campaigns = df[
        (df["Tactic Start Date"] <= current_date)
        & (df["Tactic End Date"] >= current_date)
    ].copy()

    future_campaigns = df[df["Tactic Start Date"] > current_date].copy()

    past_campaigns = df[df["Tactic End Date"] < current_date].copy()

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


def get_unique_filename(base_path: Path) -> Path:
    """
    Generate a unique filename by adding a timestamp and sequence number if needed

    Args:
        base_path: Base path for the file

    Returns:
        Path: Unique file path
    """
    directory = base_path.parent
    base_name = base_path.stem
    extension = base_path.suffix

    counter = 1
    new_path = base_path

    while new_path.exists():
        timestamp = datetime.now().strftime("%H%M%S")
        new_name = f"{base_name}_{timestamp}_{counter}{extension}"
        new_path = directory / new_name
        counter += 1

    return new_path


def write_campaign_details(
    md_file: Any, campaign: pd.Series, indent_level: int = 0
) -> None:
    """Write campaign details to markdown file"""
    indent = "  " * indent_level
    start_date = format_date(pd.to_datetime(campaign["Tactic Start Date"]))
    end_date = format_date(pd.to_datetime(campaign["Tactic End Date"]))
    budget = campaign["Tactic Allocated Budget"]

    changes = campaign.get("changes", [])
    change_indicator = "⚠️ " if changes and changes != ["New Campaign"] else ""

    md_file.write(
        f"{indent}- **{change_indicator}{campaign['Retailer']}** - {campaign['Tactic Brand']}\n"
    )

    if changes and changes == ["New Campaign"]:
        md_file.write(f"{indent}  - 🆕 **New Campaign**\n")

    md_file.write(f"{indent}  - Event: {campaign['Event Name']}\n")
    md_file.write(f"{indent}  - Product: {campaign['Tactic Product']}\n")
    md_file.write(f"{indent}  - Campaign: {campaign['Tactic Name']}\n")
    if campaign["Tactic Vendor"]:
        md_file.write(f"{indent}  - Vendor: {campaign['Tactic Vendor']}\n")
    md_file.write(f"{indent}  - Dates: {start_date} to {end_date}\n")
    md_file.write(f"{indent}  - Budget: {format_budget(budget)}\n")
    md_file.write(f"{indent}  - Order ID: {campaign['Tactic Order ID']}\n")

    if changes and changes != ["New Campaign"]:
        md_file.write(f"{indent}  - **Changes Detected:**\n")
        for change in changes:
            md_file.write(f"{indent}    - {change}\n")

    md_file.write(f"{indent}  - [ ] Campaign Setup Complete\n")
    md_file.write(f"{indent}  - [ ] Creative Assets Received\n")
    md_file.write(f"{indent}  - [ ] Campaign Launch Verified\n\n")


def write_campaign_section(
    md_file: Any, campaigns: pd.DataFrame, section_title: str
) -> None:
    """Write a section of campaigns to markdown file"""
    if not campaigns.empty:
        total_budget = campaigns["Tactic Allocated Budget"].sum()
        campaign_count = len(campaigns)

        changed_campaigns = len([c for c in campaigns["changes"] if c])
        change_indicator = (
            f" (🔄 {changed_campaigns} with changes)" if changed_campaigns else ""
        )

        md_file.write(
            f"# {section_title} ({campaign_count} Campaigns{change_indicator})\n"
        )
        md_file.write(f"**Total Budget: {format_budget(total_budget)}**\n\n")

        for retailer in sorted(campaigns["Retailer"].unique()):
            retailer_campaigns = campaigns[campaigns["Retailer"] == retailer]
            retailer_budget = retailer_campaigns["Tactic Allocated Budget"].sum()

            md_file.write(f"## {retailer} ({format_budget(retailer_budget)})\n\n")

            for _, campaign in retailer_campaigns.iterrows():
                write_campaign_details(md_file, campaign)

        md_file.write("---\n\n")
    else:
        md_file.write(f"# {section_title} (0 Campaigns)\n")
        md_file.write("*No campaigns in this category.*\n\n---\n\n")


def generate_checklist(df: pd.DataFrame, history_dir: Path, output_path: Path) -> None:
    """
    Generate the campaign checklist report

    Args:
        df: Campaign data
        history_dir: Directory containing historical data
        output_path: Path to save the generated report
    """
    logging.info(f"Generating checklist and saving to {output_path}")
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Load historical data and find changes
    historical_df = load_historical_data(history_dir)
    df = find_changes(df, historical_df)

    # Save current data as historical
    save_historical_data(df, history_dir)

    # Categorize campaigns
    current_campaigns, future_campaigns, past_campaigns = categorize_campaigns(df)

    with open(output_path, "w", encoding="utf-8") as md_file:
        md_file.write(f"# Campaign Status Report - Generated on {current_date}\n\n")

        # Summary section
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
        md_file.write(
            f"- Total Budget Across All Campaigns: {format_budget(total_budget)}\n\n"
        )

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


def write_email_section(
    campaigns: pd.DataFrame, section_title: str, indent_level: int = 0
) -> str:
    """Generate email section content"""
    lines = []
    indent = "  " * indent_level

    if not campaigns.empty:
        total_budget = campaigns["Tactic Allocated Budget"].sum()
        campaign_count = len(campaigns)
        changed_campaigns = len([c for c in campaigns["changes"] if c])

        lines.append(f"{indent}{section_title} ({campaign_count} Campaigns)")
        if changed_campaigns:
            lines.append(f"{indent}{changed_campaigns} campaigns have changes")
        lines.append(f"{indent}Total Budget: {format_budget(total_budget)}")
        lines.append("")

        for retailer in sorted(campaigns["Retailer"].unique()):
            retailer_campaigns = campaigns[campaigns["Retailer"] == retailer]
            retailer_budget = retailer_campaigns["Tactic Allocated Budget"].sum()

            lines.append(f"{indent}{retailer} ({format_budget(retailer_budget)})")
            lines.append("")

            for _, campaign in retailer_campaigns.iterrows():
                lines.append(format_campaign_for_email(campaign, indent_level + 1))

        lines.append("-" * 80)
        lines.append("")
    else:
        lines.extend(
            [
                f"{indent}{section_title} (0 Campaigns)",
                f"{indent}No campaigns in this category.",
                "",
                "-" * 80,
                "",
            ]
        )

    return "\n".join(lines)


def generate_email_report(df: pd.DataFrame, output_path: Path) -> None:
    """Generate email-friendly campaign report"""
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Categorize campaigns
    current_campaigns, future_campaigns, past_campaigns = categorize_campaigns(df)

    # Calculate summary statistics
    total_budget = df["Tactic Allocated Budget"].sum()
    total_changes = len([c for c in df["changes"] if c])
    new_campaigns = len([c for c in df["changes"] if c == ["New Campaign"]])

    lines = [
        f"Campaign Status Report - {current_date}",
        "=" * 80,
        "",
        "SUMMARY",
        "-------",
    ]

    if total_changes > 0:
        lines.append(f"Changes Detected: {total_changes} campaigns updated")
    if new_campaigns > 0:
        lines.append(f"New Campaigns: {new_campaigns}")

    lines.extend(
        [
            f"Currently Active Campaigns: {len(current_campaigns)}",
            f"Upcoming Campaigns: {len(future_campaigns)}",
            f"Completed Campaigns: {len(past_campaigns)}",
            f"Total Budget Across All Campaigns: {format_budget(total_budget)}",
            "",
            "=" * 80,
            "",
        ]
    )

    # Add each section
    sections = [
        ("CURRENTLY ACTIVE CAMPAIGNS", current_campaigns),
        ("UPCOMING CAMPAIGNS", future_campaigns),
        ("COMPLETED CAMPAIGNS", past_campaigns),
    ]

    for title, campaigns in sections:
        lines.append(write_email_section(campaigns, title))

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_reports(
    df: pd.DataFrame, history_dir: Path, output_dir: Path
) -> Tuple[Path, Path]:
    """Generate both markdown and email reports"""
    logging.info("Generating markdown and email reports")

    # Load historical data and find changes
    historical_df = load_historical_data(history_dir)
    df = find_changes(df, historical_df)

    # Save current data as historical
    save_historical_data(df, history_dir)

    # Create output filenames
    timestamp = datetime.now().strftime("%Y%m%d")
    base_md_path = output_dir / f"Campaign_Status_Report_{timestamp}.md"
    base_email_path = output_dir / f"Campaign_Status_Email_{timestamp}.txt"

    md_path = get_unique_filename(base_md_path)
    email_path = get_unique_filename(base_email_path)

    # Generate both reports
    generate_checklist(df, history_dir, md_path)
    generate_email_report(df, email_path)

    return md_path, email_path


def send_reports_by_email(
    md_path: Path,
    txt_path: Path,
) -> bool:
    """
    Convenience function to send campaign reports via email using environment configuration

    Args:
        md_path: Path to markdown report file
        txt_path: Path to text report file

    Returns:
        bool: True if email was sent successfully
    """
    try:
        config = EmailConfig.from_env()
        emailer = CampaignReportEmailer(config)
        return emailer.send_campaign_report(
            md_path, txt_path, report_date=datetime.now().strftime("%Y-%m-%d")
        )
    except Exception as e:
        logging.error(f"Failed to send reports by email: {e}")
        return False


def main(config_path: str) -> None:
    """
    Main function to run the campaign report generator and send email reports

    Args:
        config_path: Path to configuration YAML file
    """
    try:
        setup_logging()
        config = Config.from_yaml(config_path)

        # Ensure output directory exists
        config.output_dir.mkdir(parents=True, exist_ok=True)

        # Read and process data
        df = read_and_clean_data(config.input_csv)

        # Set up history directory
        history_dir = config.output_dir / "campaign_history"
        history_dir.mkdir(exist_ok=True)

        # Generate both reports
        md_path, email_path = generate_reports(df, history_dir, config.output_dir)
        logging.info(
            f"Reports generated and saved to:\nMarkdown: {md_path}\nEmail: {email_path}"
        )

        # Send email if configured
        if os.getenv("EMAIL_SENDER"):
            logging.info("Email configuration found. Attempting to send reports...")
            success = send_reports_by_email(md_path=md_path, txt_path=email_path)
            if success:
                logging.info("Campaign reports sent successfully via email")
            else:
                logging.error("Failed to send campaign reports via email")
        else:
            logging.info("No email configuration found. Skipping email send.")

        logging.info("Campaign report generation completed")

    except CampaignReportError as e:
        logging.error(f"Failed to generate reports: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Campaign Status Reports",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config", type=str, default="config.yaml", help="Path to configuration file"
    )
    args = parser.parse_args()
    main(args.config)
