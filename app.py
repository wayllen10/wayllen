
import streamlit as st
import asyncio
import websockets
import json
from threading import Thread
from queue import Queue
import time
import matplotlib.pyplot as plt

st.set_page_config(page_title="BTC Liquidez - Binance", layout="centered")
st.title("📉 Desequilíbrio de Book BTC/USDT - Binance Spot (Top 5)")

symbol = "btcusdt"
DEPTH = 5
data_queue = Queue()

# Coleta dados do WebSocket
async def coletar_book():
    url = f"wss://stream.binance.com:9443/ws/{symbol}@depth{DEPTH}@100ms"
    async with websockets.connect(url) as ws:
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            bids = data.get("bids", [])
            asks = data.get("asks", [])
            data_queue.put((bids, asks))

def iniciar_coleta():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(coletar_book())

# Inicia a thread de WebSocket
if 'ws_started' not in st.session_state:
    thread = Thread(target=iniciar_coleta, daemon=True)
    thread.start()
    st.session_state.ws_started = True

placeholder = st.empty()
chart_placeholder = st.empty()

def calcular_totais(bids, asks, nivel=DEPTH):
    bid_total = sum(float(qty) for price, qty in bids[:nivel])
    ask_total = sum(float(qty) for price, qty in asks[:nivel])
    return bid_total, ask_total

# Loop de atualização
while True:
    if not data_queue.empty():
        bids, asks = data_queue.get()
        bid_total, ask_total = calcular_totais(bids, asks)
        total = bid_total + ask_total
        if total == 0:
            continue

        bid_pct = (bid_total / total) * 100
        ask_pct = (ask_total / total) * 100
        desequilibrio = bid_pct - ask_pct
        cor = "🔼 Compra Forte" if desequilibrio > 5 else "🔽 Venda Forte" if desequilibrio < -5 else "⏸️ Equilíbrio"

        with placeholder.container():
            st.metric("💚 Volume de Compra (Top 5)", f"{bid_total:,.2f}", delta=f"{bid_pct:.1f}%")
            st.metric("❤️ Volume de Venda (Top 5)", f"{ask_total:,.2f}", delta=f"{ask_pct:.1f}%")
            st.subheader(f"Desequilíbrio: **{desequilibrio:+.1f}%** {cor}")

        # Gráfico de pizza ainda menor
        fig, ax = plt.subplots(figsize=(2.8, 2.8))  # Reduzido ainda mais
        ax.pie([bid_pct, ask_pct],
               labels=["Buy (BIDs)", "Sell (ASKs)"],
               autopct='%1.1f%%',
               startangle=90,
               colors=["limegreen", "lightcoral"])
        ax.set_title("Distribuição de Liquidez BTC (Top 5 níveis)", fontsize=10)
        chart_placeholder.pyplot(fig)
        plt.close(fig)

    time.sleep(0.5)
