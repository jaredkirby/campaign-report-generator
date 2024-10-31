# Campaign Report Generator

A Python-based tool that generates formatted Markdown and email reports for tracking media campaign status across different retailers. The tool tracks changes between report generations, highlights new campaigns, organizes campaigns by their current status, and can automatically distribute reports via email.

## Features

- Automatically categorizes campaigns into active, upcoming, and completed
- Organizes upcoming campaigns by month for better planning
- Tracks and highlights changes between report generations
- Maintains historical versions of campaign data
- Generates both Markdown reports and email-friendly formats
- Shows budget allocations at campaign, retailer, and monthly levels
- Includes campaign status checklists for setup tracking
- Automated email distribution of reports
- Automatic cleanup of old report files

## Prerequisites

- Python 3.8+
- pandas
- pyyaml
- python-dotenv

## Installation

1. Clone the repository:
```bash
git clone https://github.com/jaredkirby/campaign-report-generator.git
cd campaign-report-generator
```

2. Install required packages:
```bash
pip install pandas pyyaml python-dotenv
```

## Configuration

### Basic Configuration
Create a `config.yaml` file in the project directory:

```yaml
input_offsite_csv: "path/to/your/input.csv"
output_dir: "path/to/output/directory"
```

### Email Configuration
Create a `.env` file in the project directory with your email settings:

```env
EMAIL_SMTP_SERVER=smtp.office365.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER=your-email@example.com
EMAIL_SENDER_PASSWORD=your-password
EMAIL_PRIMARY_RECIPIENTS=recipient1@example.com,recipient2@example.com
EMAIL_CC_RECIPIENTS=cc1@example.com,cc2@example.com
```

Create **`reports`** and **`output`** directories in the project directory to store the input files and generated outputs, respectively.

## Input File Format

The tool expects a CSV file with the following columns:

- Tactic Start Date
- Tactic End Date
- Tactic Vendor
- Retailer
- Tactic Brand
- Event Name
- Tactic Name
- Tactic Product
- Tactic Order ID
- Tactic Allocated Budget

> **Note**: Use the Report Engine in Shopperations to generate a properly formatted CSV file.

Example CSV format:
```csv
"Tactic Start Date","Tactic End Date","Retailer","Tactic Brand","Event Name","Tactic Name","Tactic Vendor","Tactic Product","Budget Type","Tactic Order ID","Tactic Allocated Budget"
"2024-01-01","2024-01-31","ExampleRetailer","BrandName","EventName","CampaignType","VendorName","ProductName","Working","12345-01","50000"
```

## Usage

Run the script:
```bash
python campaign_report.py --config config.yaml
```

The tool will:
1. Read the input CSV file
2. Compare with previous report data (if any)
3. Generate both Markdown and email-friendly reports
4. Save a versioned copy of the campaign data for future change tracking
5. Send email reports if configured
6. Clean up old report files (configurable retention period)

## Output

The tool generates three types of files:

1. Campaign Status Report (`Campaign_Status_Report_YYYYMMDD_HHMMSS.md`):
   - Summary of all campaigns
   - Budget totals
   - Campaign details grouped by status and retailer
   - Monthly organization for upcoming campaigns
   - Change indicators for modified campaigns

2. Email Report (`Campaign_Status_Email_YYYYMMDD_HHMMSS.txt`):
   - Email-friendly text format of the campaign status
   - Same organization as the Markdown report
   - Optimized for email reading

3. Historical Data (`campaign_history/campaign_history_YYYYMMDD_HHMMSS.json`):
   - Versioned snapshots of campaign data
   - Used for change tracking between reports

### Change Indicators

The report uses the following indicators:
- ⚠️ Campaign has changes
- 🆕 New campaign
- 🔄 Number of changes in section

## Report Sections

Each report includes:
1. Summary statistics
2. Currently Active Campaigns (grouped by retailer)
3. Upcoming Campaigns (grouped by month, then retailer)
4. Completed Campaigns (grouped by retailer)

Each campaign entry shows:
- Event details
- Product information
- Budget allocation
- Date range
- Vendor information
- Setup status checklist
- Change history (if applicable)

## Email Distribution

When email configuration is present, the tool will:
- Send reports to specified primary recipients
- CC additional stakeholders as configured
- Include the report content in the email body
- Attach the Markdown version for reference
- Use a standardized subject line with the report date

## Report Cleanup

The tool automatically manages report history:
- Keeps reports for a configurable number of days (default: 30)
- Automatically removes older report files
- Maintains a clean output directory
- Preserves historical data for change tracking

## Troubleshooting

Common issues:
1. Missing columns in input CSV:
   - Ensure all required columns are present
   - Check column names match exactly

2. Date format issues:
   - Dates should be in YYYY-MM-DD format
   - Remove any summary or total rows

3. Budget format issues:
   - Budget values should be numbers
   - Remove any currency symbols or commas

4. Email configuration issues:
   - Verify SMTP settings
   - Check email credentials
   - Ensure recipient addresses are valid
   - Check firewall/security settings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.