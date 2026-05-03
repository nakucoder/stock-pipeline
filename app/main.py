from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from app.stocks import fetch_stock_prices
from app.storage import save_to_s3
from app.config import PIPELINE_INTERVAL_MINUTES

app = FastAPI(title="Stock Price Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache
_cache = {"data": None}

def run_pipeline():
    print("Running stock pipeline...")
    stock_data = fetch_stock_prices()
    if stock_data:
        _cache["data"] = stock_data
        save_to_s3(stock_data)

run_pipeline()

scheduler = BackgroundScheduler()
scheduler.add_job(run_pipeline, "interval", minutes=PIPELINE_INTERVAL_MINUTES)
scheduler.start()

@app.get("/")
def root():
    return {"message": "Stock Price Pipeline is running"}

@app.get("/health")
def health():
    return {"status": "healthy", "scheduler": "running"}

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
