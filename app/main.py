from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from app.stocks import fetch_stock_prices
from app.storage import save_to_s3
from datetime import datetime, timedelta
import pytz
import boto3
import json
from app.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME, AWS_REGION

app = FastAPI(title="Stock Price Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache
_cache = {"data": None}

def is_market_hours():
    est = pytz.timezone("America/New_York")
    now = datetime.now(est)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close

def run_pipeline():
    if not is_market_hours():
        print("Market closed - skipping Alpha Vantage call, serving cache")
        return
    print("Running stock pipeline...")
    stock_data = fetch_stock_prices()
    if stock_data:
        _cache["data"] = stock_data
        save_to_s3(stock_data)

# Run once on startup to populate cache
run_pipeline()

scheduler = BackgroundScheduler()
scheduler.add_job(run_pipeline, "interval", hours=4)
scheduler.start()

@app.get("/")
def root():
    return {"message": "Stock Price Pipeline is running"}

@app.get("/health")
def health():
    market_open = is_market_hours()
    return {"status": "healthy", "scheduler": "running", "market_open": market_open}

@app.get("/prices")
def get_prices():
    if _cache["data"]:
        return {"status": "success", "data": _cache["data"]}
    return {"status": "error", "message": "Failed to fetch stock data"}

@app.get("/run")
def trigger_pipeline():
    stock_data = fetch_stock_prices()
    if stock_data:
        _cache["data"] = stock_data
        filename = save_to_s3(stock_data)
        return {"status": "success", "data": stock_data, "saved_to": filename}
    return {"status": "error", "message": "Failed to fetch stock data"}

@app.get("/history")
def get_history():
    TICKERS = ["NVDA", "AAPL", "MSFT", "VOO", "AMZN"]
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        cutoff = datetime.utcnow() - timedelta(days=7)
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=AWS_BUCKET_NAME, Prefix="stock-prices/")

        entries = []
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj.get("Key", "")
                # key: stock-prices/YYYY/MM/DD/HH-MM-SS.json
                trimmed = key.removeprefix("stock-prices/").removesuffix(".json")
                parts = trimmed.split("/")
                if len(parts) != 4:
                    continue
                try:
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    t = parts[3].split("-")
                    hour, minute = int(t[0]), int(t[1])
                    file_dt = datetime(year, month, day, hour, minute)
                except Exception:
                    continue
                if file_dt >= cutoff:
                    entries.append((file_dt, key))

        entries.sort(key=lambda x: x[0])

        results = []
        for file_dt, key in entries:
            try:
                response = s3.get_object(Bucket=AWS_BUCKET_NAME, Key=key)
                data = json.loads(response["Body"].read())
                stocks = (data or {}).get("stocks") or {}
                entry = {"time": file_dt.strftime("%m/%d %H:%M")}
                for ticker in TICKERS:
                    t = stocks.get(ticker) or {}
                    raw_change = t.get("change_percent", None)
                    try:
                        change = round(float(raw_change), 2) if raw_change is not None else None
                    except Exception:
                        change = None
                    entry[ticker] = {
                        "price": t.get("price_usd", None),
                        "change_percent": change,
                        "volume": t.get("volume", None),
                        "high": t.get("high_usd", None),
                        "low": t.get("low_usd", None),
                    }
                results.append(entry)
            except Exception:
                continue

        return {"status": "success", "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}
