import gspread
from google.oauth2.service_account import Credentials
import praw
import prawcore
from datetime import datetime, timedelta
import time

# Reddit API credentials
reddit = praw.Reddit(
    client_id="PCz5A3g4wDn_N-UWlPzuiA",
    client_secret="qziRCLQW9BJ2N8odnob7Wlk1N0BVjw",
    user_agent="sub_checker_1.0"
)

# Google Sheets API setup
SERVICE_ACCOUNT_FILE = "/Users/kurtstrang/Sub Ticker Tracker/sub-ticker-tracker-520b9ebab389.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)

# Open the main sheet and history sheet
spreadsheet = gc.open("Subreddit growth tracker")  # Replace with your sheet's name
worksheet = spreadsheet.sheet1  # Main sheet (tab 1)
history_sheet = spreadsheet.worksheet("Subscriber History")  # Subscriber History sheet (tab 2)

# Fetch all existing data from Subscriber History
history_data = history_sheet.get_all_values()

# Get current date
current_date = datetime.now().strftime("%Y-%m-%d")

# Prepare data from Sheet1
sheet1_data = worksheet.get_all_records()
row_map = {row["Ticker"]: index + 2 for index, row in enumerate(sheet1_data)}  # Map tickers to rows

# Function to safely fetch subscriber count from Reddit
def safe_fetch_subscribers(subreddit_name, retries=0):
    """Safely fetch subreddit subscriber count with error handling and backoff."""
    try:
        subreddit = reddit.subreddit(subreddit_name)
        time.sleep(1.5)  # Rate limit: Increase delay to reduce API load
        return subreddit.subscribers
    except prawcore.exceptions.TooManyRequests:
        if retries < 5:  # Retry up to 5 times with exponential backoff
            wait_time = 2 ** retries
            print(f"Rate limit exceeded for subreddit {subreddit_name}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            return safe_fetch_subscribers(subreddit_name, retries + 1)
        else:
            print(f"Failed to fetch data for subreddit {subreddit_name} after multiple retries.")
            return None
    except Exception as e:
        print(f"Error fetching data for subreddit {subreddit_name}: {e}")
        return None

# Function to retrieve historical counts from Subscriber History
def get_historical_count(history_data, subreddit_name, target_date, tolerance_days=5):
    """Retrieve the closest subscriber count for a subreddit near the target date."""
    closest_record = None
    closest_diff = float('inf')  # Start with a large difference

    target_date_obj = datetime.strptime(target_date, "%Y-%m-%d")

    for record in history_data:
        if record[0] == subreddit_name:  # Match subreddit name
            try:
                record_date = datetime.strptime(record[1], "%Y-%m-%d")
                date_diff = abs((record_date - target_date_obj).days)

                if date_diff <= tolerance_days and date_diff < closest_diff:
                    closest_record = record
                    closest_diff = date_diff
            except ValueError:
                # Skip malformed dates
                continue

    if closest_record:
        print(f"Found historical record for {subreddit_name} on {closest_record[1]}: {closest_record[2]}")
    else:
        print(f"No historical data found for {subreddit_name} near {target_date} within {tolerance_days} days.")
    return int(closest_record[2]) if closest_record else None

# Function to calculate growth rate
def calculate_growth(current, previous):
    """Calculate percentage growth."""
    return ((current - previous) / previous * 100) if previous else 0

# Prepare batch updates for Sheet1 and Subscriber History
batch_updates = []
history_updates = []
for row in sheet1_data:
    ticker = row["Ticker"]
    subreddit_url = row.get("Subreddit URL")
    if not subreddit_url:
        continue

    # Extract subreddit name
    subreddit_name = subreddit_url.split("/")[-1]

    # Fetch current subscriber count
    subscriber_count = safe_fetch_subscribers(subreddit_name)
    if subscriber_count is None:
        continue

    # Add data to history sheet update
    history_updates.append([subreddit_name, current_date, subscriber_count])

    # Calculate historical target dates
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    one_month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    three_months_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    # Retrieve historical counts
    prev_week_count = get_historical_count(history_data, subreddit_name, one_week_ago, tolerance_days=5) or 0
    prev_month_count = get_historical_count(history_data, subreddit_name, one_month_ago, tolerance_days=5) or 0
    prev_three_month_count = get_historical_count(history_data, subreddit_name, three_months_ago, tolerance_days=5) or 0

    # Calculate growth rates
    weekly_growth = calculate_growth(subscriber_count, prev_week_count)
    monthly_growth = calculate_growth(subscriber_count, prev_month_count)
    three_month_growth = calculate_growth(subscriber_count, prev_three_month_count)

    # **LOG DETAILS**:
    print(f"Subreddit: {subreddit_name}")
    print(f"  Current Subscribers: {subscriber_count}")
    print(f"  Previous Week Subscribers: {prev_week_count} | Weekly Growth: {weekly_growth:.2f}%")
    print(f"  Previous Month Subscribers: {prev_month_count} | Monthly Growth: {monthly_growth:.2f}%")
    print(f"  Previous Three-Month Subscribers: {prev_three_month_count} | Three-Month Growth: {three_month_growth:.2f}%")

    # Append the update to the batch
    row_number = row_map[ticker]
    batch_updates.append(
        {
            "range": f"D{row_number}:K{row_number}",
            "values": [[
                current_date,  # Column D
                subscriber_count,  # Column E
                prev_week_count,  # Column F
                f"{weekly_growth:.2f}%",  # Column G
                prev_month_count,  # Column H
                f"{monthly_growth:.2f}%",  # Column I
                prev_three_month_count,  # Column J
                f"{three_month_growth:.2f}%",  # Column K
            ]]
        }
    )

# Perform batch updates to the main sheet
if batch_updates:
    try:
        worksheet.batch_update(batch_updates)
    except Exception as e:
        print(f"Error performing batch update to the main sheet: {e}")

# Perform batch updates to the history sheet
if history_updates:
    try:
        history_sheet.append_rows(history_updates)
    except Exception as e:
        print(f"Error updating Subscriber History: {e}")

print("Script execution complete.")
