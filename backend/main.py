from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

from datetime import datetime

from dotenv import load_dotenv

import requests

from models import PriceInfo
from typing import List
from models import CandleInfo
from models import OrderRequest

from client import BinanceTestClient
from models import AccountInfo, OrderRequest

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
client = BinanceTestClient(api_key, api_secret)


@app.get("/api/health")
async def health():
    return {"message": "OK"}


@app.get("/api/account")
async def get_account() -> AccountInfo:
    try:
        print("🔁 Llamando al endpoint /api/account")
        response = client._execute_request("/v3/account", {}, method="GET")
        data = response.json()

        balances = {item['asset']: item['free'] for item in data['balances']}

        return AccountInfo(
            uid=data.get("accountId", 0),
            account_type=data.get("accountType", "SPOT"),
            btc_balance={"asset": "BTC", "balance": balances.get("BTC", "0.0")},
            usdt_balance={"asset": "USDT", "balance": balances.get("USDT", "0.0")},
            eth_balance={"asset": "ETH", "balance": balances.get("ETH", "0.0")},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/api/price")
async def get_price(symbol: str) -> PriceInfo:
    try:
        response = requests.get(
            f"https://testnet.binance.vision/api/v3/ticker/price",
            params={"symbol": symbol}
        )
        response.raise_for_status()
        data = response.json()
        return PriceInfo(symbol=data["symbol"], price=data["price"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/price-history", response_model=List[CandleInfo])
async def get_price_history(symbol: str, interval: str = '1h', limit: int = 100):
    try:
        response = requests.get(
            "https://testnet.binance.vision/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit}
        )
        response.raise_for_status()
        raw_data = response.json()

        candles = [
            CandleInfo(
                open_time=datetime.fromtimestamp(c[0] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
                open=float(c[1]),
                high=float(c[2]),
                low=float(c[3]),
                close=float(c[4]),
                volume=float(c[5]),
                close_time=datetime.fromtimestamp(c[6] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
                quote_asset_volume=float(c[7]),
                number_of_trades=int(c[8]),
                taker_buy_base_asset_volume=float(c[9]),
                taker_buy_quote_asset_volume=float(c[10]),
                ignore=c[11]
            )
            for c in raw_data
        ]
        return candles
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/order")
async def create_order(order: OrderRequest):
    try:
        print(f"Enviando orden: {order.dict()}")
        endpoint = "/v3/order/test" if order.test else "/v3/order"

        params = {
            "symbol": order.symbol,
            "side": order.side.upper(),
            "type": order.order_type.upper(),
            "quantity": order.quantity
        }

        response = client._execute_request(endpoint, params, method="POST")
        if order.test:
            return {"message": "Test order sent successfully "}
        else:
            return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
