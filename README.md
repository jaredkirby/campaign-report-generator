# Campaign Report Generator

A Python-based tool that generates formatted Markdown reports for tracking media campaign status across different retailers. The tool tracks changes between report generations, highlights new campaigns, and organizes campaigns by their current status (active, upcoming, or completed).

## Features

- Automatically categorizes campaigns into active, upcoming, and completed
- Tracks and highlights changes between report generations
- Maintains historical versions of campaign data
- Generates clear, hierarchical Markdown reports
- Shows budget allocations at campaign and retailer levels
- Includes campaign status checklists for setup tracking

## Prerequisites

- Python 3.8+
- pandas
- pyyaml

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/campaign-report-generator.git
cd campaign-report-generator
```

2. Install required packages:
```bash
pip install pandas pyyaml
```

## Configuration

Create a `config.yaml` file in the project directory:

```yaml
input_offsite_csv: "path/to/your/input.csv"
output_dir: "path/to/output/directory"
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
3. Generate a Markdown report in the specified output directory
4. Save a versioned copy of the campaign data for future change tracking

## Output

The tool generates two types of files:

1. Campaign Status Report (`Campaign_Status_Report_YYYYMMDD_HHMMSS.md`):
   - Summary of all campaigns
   - Budget totals
   - Campaign details grouped by status and retailer
   - Change indicators for modified campaigns

2. Historical Data (`campaign_history/campaign_history_YYYYMMDD_HHMMSS.json`):
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
2. Currently Active Campaigns
3. Upcoming Campaigns
4. Completed Campaigns

Each campaign entry shows:
- Event details
- Product information
- Budget allocation
- Date range
- Vendor information
- Setup status checklist

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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.