import unittest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Import necessary functions from your main code
from auditor_email import (
    find_changes,
    get_campaign_hash,
    format_budget,
    format_date,
)


class TestChangeHighlighting(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        # Create base test data
        self.current_date = datetime.now()
        self.base_campaign = {
            "Tactic Order ID": "12345",
            "Retailer": "Test Retailer",
            "Tactic Brand": "Test Brand",
            "Event Name": "Test Event",
            "Tactic Start Date": self.current_date,
            "Tactic End Date": self.current_date + timedelta(days=30),
            "Tactic Vendor": "Test Vendor",
            "Tactic Product": "Test Product",
            "Tactic Allocated Budget": 1000.00,
            "Tactic Name": "Test Campaign",
        }

    def create_test_dataframe(self, data_list):
        """Helper function to create test DataFrame"""
        df = pd.DataFrame(data_list)
        # Ensure date columns are datetime type
        if "Tactic Start Date" in df.columns:
            df["Tactic Start Date"] = pd.to_datetime(df["Tactic Start Date"])
        if "Tactic End Date" in df.columns:
            df["Tactic End Date"] = pd.to_datetime(df["Tactic End Date"])
        return df

    def test_campaign_hash(self):
        """Test campaign hash generation"""
        # Create test campaign
        df = self.create_test_dataframe([self.base_campaign])

        # Generate hash
        hash1 = get_campaign_hash(df.iloc[0])

        # Modify non-key field
        modified_campaign = self.base_campaign.copy()
        modified_campaign["Tactic Allocated Budget"] = 2000.00
        df_modified = self.create_test_dataframe([modified_campaign])
        hash2 = get_campaign_hash(df_modified.iloc[0])

        # Hashes should be identical for non-key field changes
        self.assertEqual(hash1, hash2)

        # Modify key field
        modified_campaign["Tactic Order ID"] = "67890"
        df_modified = self.create_test_dataframe([modified_campaign])
        hash3 = get_campaign_hash(df_modified.iloc[0])

        # Hashes should be different for key field changes
        self.assertNotEqual(hash1, hash3)

    def test_new_campaign_detection(self):
        """Test detection of new campaigns"""
        # Current data with one campaign
        current_data = [self.base_campaign.copy()]
        current_df = self.create_test_dataframe(current_data)

        # Empty historical data (different from None)
        historical_df = self.create_test_dataframe([])

        # Find changes
        result_df = find_changes(current_df, historical_df)

        # Verify changes
        self.assertEqual(len(result_df), 1)
        self.assertEqual(result_df.iloc[0]["changes"], ["New Campaign"])

        # Test with None historical data
        result_df = find_changes(current_df, None)
        self.assertEqual(len(result_df), 1)
        self.assertEqual(
            result_df.iloc[0]["changes"], []
        )  # Should be empty list for None historical data

    def test_budget_change_detection(self):
        """Test detection of budget changes"""
        # Current data
        current_data = [self.base_campaign.copy()]
        current_df = self.create_test_dataframe(current_data)

        # Historical data with different budget
        historical_campaign = self.base_campaign.copy()
        historical_campaign["Tactic Allocated Budget"] = 800.00
        historical_df = self.create_test_dataframe([historical_campaign])

        # Find changes
        result_df = find_changes(current_df, historical_df)

        # Verify changes
        self.assertEqual(len(result_df), 1)
        expected_change = f"Budget changed from {format_budget(800.00)} to {format_budget(1000.00)} ({format_budget(200.00)})"
        self.assertIn(expected_change, result_df.iloc[0]["changes"])

    def test_date_change_detection(self):
        """Test detection of date changes"""
        # Current data
        current_data = [self.base_campaign.copy()]
        current_df = self.create_test_dataframe(current_data)

        # Historical data with different dates
        historical_campaign = self.base_campaign.copy()
        historical_campaign["Tactic Start Date"] = self.current_date - timedelta(days=5)
        historical_df = self.create_test_dataframe([historical_campaign])

        # Find changes
        result_df = find_changes(current_df, historical_df)

        # Verify changes
        self.assertEqual(len(result_df), 1)
        expected_change = (
            f"Start Date changed from "
            f"{format_date(self.current_date - timedelta(days=5))} to "
            f"{format_date(self.current_date)}"
        )
        self.assertIn(expected_change, result_df.iloc[0]["changes"])

    def test_multiple_changes_detection(self):
        """Test detection of multiple changes in one campaign"""
        # Current data
        current_data = [self.base_campaign.copy()]
        current_df = self.create_test_dataframe(current_data)

        # Historical data with multiple differences
        historical_campaign = self.base_campaign.copy()
        historical_campaign["Tactic Allocated Budget"] = 800.00
        historical_campaign["Tactic Vendor"] = "Old Vendor"
        historical_campaign["Tactic Product"] = "Old Product"
        historical_df = self.create_test_dataframe([historical_campaign])

        # Find changes
        result_df = find_changes(current_df, historical_df)

        # Verify changes
        self.assertEqual(len(result_df), 1)
        changes = result_df.iloc[0]["changes"]
        self.assertEqual(len(changes), 3)  # Should detect all three changes
        self.assertTrue(any("Budget changed" in change for change in changes))
        self.assertTrue(any("Vendor changed" in change for change in changes))
        self.assertTrue(any("Product changed" in change for change in changes))

    def test_no_changes_detection(self):
        """Test when no changes are present"""
        # Current data
        current_data = [self.base_campaign.copy()]
        current_df = self.create_test_dataframe(current_data)

        # Identical historical data
        historical_df = self.create_test_dataframe([self.base_campaign.copy()])

        # Find changes
        result_df = find_changes(current_df, historical_df)

        # Verify no changes detected
        self.assertEqual(len(result_df), 1)
        self.assertEqual(len(result_df.iloc[0]["changes"]), 0)

    def test_multiple_campaigns(self):
        """Test change detection with multiple campaigns"""
        # Create multiple campaigns with different changes
        campaign1 = self.base_campaign.copy()
        campaign2 = self.base_campaign.copy()
        campaign2["Tactic Order ID"] = "67890"
        campaign2["Tactic Allocated Budget"] = 2000.00

        current_df = self.create_test_dataframe([campaign1, campaign2])

        # Historical data with changes in one campaign
        historical_campaign1 = campaign1.copy()
        historical_campaign2 = campaign2.copy()
        historical_campaign2["Tactic Allocated Budget"] = 1500.00

        historical_df = self.create_test_dataframe(
            [historical_campaign1, historical_campaign2]
        )

        # Find changes
        result_df = find_changes(current_df, historical_df)

        # Verify changes
        self.assertEqual(len(result_df), 2)
        self.assertEqual(
            len(result_df.iloc[0]["changes"]), 0
        )  # No changes in first campaign
        self.assertEqual(
            len(result_df.iloc[1]["changes"]), 1
        )  # One change in second campaign


def run_tests():
    """Run test suite"""
    unittest.main(argv=[""], verbosity=2, exit=False)


if __name__ == "__main__":
    run_tests()
