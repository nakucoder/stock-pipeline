from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from app.stocks import fetch_stock_prices
from app.storage import save_to_s3
from datetime import datetime
import pytz

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
