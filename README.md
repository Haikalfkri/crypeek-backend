# 🪙 Cryptocurrency Price Prediction System - Backend (Django)

This is the backend system for the Cryptocurrency Price Prediction App, built using Django REST Framework. It provides API endpoints for fetching crypto data, storing historical prices, generating predictions using machine learning, and summarizing sentiment and analysis using a language model.

---

## 📦 Features

- 🔐 JWT Authentication (Login/Register)
- 📊 Historical crypto data storage (daily/hourly)
- 🤖 ML-powered price prediction (LSTM or other models)
- 🧠 Sentiment and news analysis using LLM (via TogetherAI/Groq)
- 📈 API endpoints for coin charts, predictions, and market data
- 🗃️ Admin panel for managing coins, predictions, and news
- 📰 News fetching and sentiment tagging from external APIs

---

## ⚙️ Tech Stack

- **Backend**: Django, Django REST Framework
- **Database**: PostgreSQL / SQLite (default)
- **ML Model**: LSTM (trained using historical close price)
- **External APIs**: CoinGecko, CryptoCompare, NewsAPI
- **LLM Integration**: Together AI / Groq (for analysis summary)

---
