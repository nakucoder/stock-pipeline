from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from app.stocks import fetch_stock_prices
from app.storage import save_to_s3
from app.config import PIPELINE_INTERVAL_MINUTES

app = FastAPI(
    title="Stock Price Pipeline",
    description="Automated stock price pipeline — NVDA, AAPL, MSFT, VOO, AMZN",
    version="1.0.0"
)

def run_pipeline():
    print("Running stock pipeline...")
    stock_data = fetch_stock_prices()
    if stock_data:
        save_to_s3(stock_data)
        print(f"Pipeline complete: {stock_data['timestamp']}")
    else:
        print("Pipeline failed: no data returned")

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
    """Get current stock prices without saving to S3."""
    stock_data = fetch_stock_prices()
    if stock_data:
        return {"status": "success", "data": stock_data}
    return {"status": "error", "message": "Failed to fetch stock data"}

@app.get("/run")
def trigger_pipeline():
    """Manually trigger the pipeline and save to S3."""
    stock_data = fetch_stock_prices()
    if stock_data:
        filename = save_to_s3(stock_data)
        return {"status": "success", "data": stock_data, "saved_to": filename}
    return {"status": "error", "message": "Failed to fetch stock data"}