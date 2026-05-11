# Stock Price Pipeline

An automated data pipeline that fetches real-time stock prices for NVDA, AAPL, MSFT, VOO, and AMZN and stores them in AWS S3 — built with FastAPI, Docker, and Python.

## What it does

- Fetches live stock prices from Alpha Vantage API
- Tracks NVDA, AAPL, MSFT, VOO, and AMZN
- Shows price, change, volume, and latest trading day
- Automatically saves data to AWS S3 every 60 minutes
- Organized by date: stock-prices/YYYY/MM/DD/HH-MM-SS.json

## Data Storage

- Data is saved to S3 every 60 minutes automatically during market hours (Mon–Fri, 9:30 AM – 4 PM EST)
- Scheduler runs every 4 hours during market hours only to stay within Alpha Vantage's 25 calls/day free limit
- S3 path structure: stock-prices/YYYY/MM/DD/HH-MM-SS.json
- Each file contains price, open, high, low, change, change percent, volume, previous close, and latest trading day for all 5 tickers
- The /history endpoint reads the last 7 days of S3 files and returns them as a JSON array sorted oldest to newest

## Tech Stack

- FastAPI — REST API framework
- Docker — containerized for consistent deployment
- AWS S3 — cloud storage for all pipeline data
- APScheduler — automated scheduling every 60 minutes
- Alpha Vantage API — free stock market data

## API Limits

- Alpha Vantage free tier: 25 API calls per day
- Each pipeline run makes 5 calls (one per stock)
- Scheduler is limited to market hours and runs every 4 hours to stay within the limit
- Dashboard shows cached data on weekends with a "Market Closed" banner

## Lambda Migration

API Gateway calls always serve from S3 cache instantly — no Alpha Vantage requests are made on dashboard loads. Alpha Vantage is only called when EventBridge triggers the Lambda on schedule (Mon-Fri 9:30 AM and 1:30 PM EST). This eliminates API Gateway timeouts and stays well within the 25 calls/day free tier limit.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| GET / | Check if pipeline is running |
| GET /health | Health check for monitoring |
| GET /prices | Get current stock prices |
| GET /run | Trigger pipeline and save to S3 |
| GET /history | Get last 7 days of stock prices from S3 |

## How to run it

1. Clone the repo
2. Create a .env file with your AWS and Alpha Vantage credentials
3. Run: `docker-compose up -d`
4. Test: open http://localhost:8002/prices in your browser

## Author

Juan Spinelli — [GitHub](https://github.com/nakucoder) | [LinkedIn](https://www.linkedin.com/in/juan-spinelli-85b6a1294)
