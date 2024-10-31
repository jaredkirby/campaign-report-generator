import pandas as pd
from datetime import datetime, timedelta


def generate_test_csv(filename: str, num_campaigns: int = 5):
    """Generate test CSV file with campaign data"""
    current_date = datetime.now()

    data = []
    for i in range(num_campaigns):
        campaign = {
            "Tactic Order ID": f"ORDER_{i+1:05d}",
            "Retailer": f"Retailer_{(i%3)+1}",
            "Tactic Brand": f"Brand_{(i%2)+1}",
            "Event Name": f"Event_{i+1}",
            "Tactic Start Date": current_date + timedelta(days=i * 7),
            "Tactic End Date": current_date + timedelta(days=(i * 7) + 30),
            "Tactic Vendor": f"Vendor_{(i%2)+1}",
            "Tactic Product": f"Product_{i+1}",
            "Tactic Allocated Budget": 1000.00 * (i + 1),
            "Tactic Name": f"Campaign_{i+1}",
        }
        data.append(campaign)

    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"Generated test data file: {filename}")


if __name__ == "__main__":
    # Generate initial data
    generate_test_csv("initial_campaigns.csv")

    # Generate modified data for testing changes
    generate_test_csv("updated_campaigns.csv", num_campaigns=6)  # One new campaign
