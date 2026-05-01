import os
from dotenv import load_dotenv

load_dotenv()

# AWS Settings
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")

# Alpha Vantage Settings
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

# Stocks to track
STOCKS = ["NVDA", "AAPL", "MSFT", "VOO", "AMZN"]

# Pipeline Settings
PIPELINE_INTERVAL_MINUTES = 60