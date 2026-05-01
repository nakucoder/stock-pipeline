# Stock Price Pipeline

An automated data pipeline that fetches real-time stock prices for NVDA, AAPL, MSFT, VOO, and AMZN and stores them in AWS S3 — built with FastAPI, Docker, and Python.

## What it does

- Fetches live stock prices from Alpha Vantage API
- Tracks NVDA, AAPL, MSFT, VOO, and AMZN
- Shows price, change, volume, and latest trading day
- Automatically saves data to AWS S3 every 60 minutes
- Organized by date: stock-prices/YYYY/MM/DD/HH-MM-SS.json

## Tech Stack

- FastAPI — REST API framework
- Docker — containerized for consistent deployment
- AWS S3 — cloud storage for all pipeline data
- APScheduler — automated scheduling every 60 minutes
- Alpha Vantage API — free stock market data

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| GET / | Check if pipeline is running |
| GET /health | Health check for monitoring |
| GET /prices | Get current stock prices |
| GET /run | Trigger pipeline and save to S3 |

## How to run it

1. Clone the repo
2. Create a .env file with your AWS and Alpha Vantage credentials
3. Run: docker build -t stock-pipeline . && docker run -p 8002:8000 --env-file .env stock-pipeline
4. Test: open http://localhost:8002/prices in your browser

## Author

Juan Spinelli — [GitHub](https://github.com/nakucoder) | [LinkedIn](https://www.linkedin.com/in/juan-spinelli-85b6a1294)
