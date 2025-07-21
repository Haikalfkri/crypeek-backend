import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import (
    BTCUSDTDetail, ETHUSDTDetail, BNBUSDTDetail, SOLUSDTDetail, XRPUSDTDetail,
    TONUSDTDetail, ADAUSDTDetail, DOGEUSDTDetail, AVAXUSDTDetail, LINKUSDTDetail,
    DOTUSDTDetail, MATICUSDTDetail, ICPUSDTDetail, LTCUSDTDetail, SHIBUSDTDetail,
    BCHUSDTDetail, UNIUSDTDetail, APTUSDTDetail, NEARUSDTDetail, XLMUSDTDetail
)
import os
import time

COINS = {
    'BTC': ('bitcoin', BTCUSDTDetail),
    'ETH': ('ethereum', ETHUSDTDetail),
    'BNB': ('binancecoin', BNBUSDTDetail),
    'SOL': ('solana', SOLUSDTDetail),
    'XRP': ('ripple', XRPUSDTDetail),
    'TON': ('the-open-network', TONUSDTDetail),
    'ADA': ('cardano', ADAUSDTDetail),
    'DOGE': ('dogecoin', DOGEUSDTDetail),
    'AVAX': ('avalanche-2', AVAXUSDTDetail),
    'LINK': ('chainlink', LINKUSDTDetail),
    'DOT': ('polkadot', DOTUSDTDetail),
    'MATIC': ('matic-network', MATICUSDTDetail),
    'ICP': ('internet-computer', ICPUSDTDetail),
    'LTC': ('litecoin', LTCUSDTDetail),
    'SHIB': ('shiba-inu', SHIBUSDTDetail),
    'BCH': ('bitcoin-cash', BCHUSDTDetail),
    'UNI': ('uniswap', UNIUSDTDetail),
    'APT': ('aptos', APTUSDTDetail),
    'NEAR': ('near', NEARUSDTDetail),
    'XLM': ('stellar', XLMUSDTDetail),
}

CRYPTO_COMPARE_API_KEY = os.environ.get("CRYPTO_COMPARE_API_KEY")

class Command(BaseCommand):
    help = 'Fetch full hourly + market + description + % change from CryptoCompare & CoinGecko'

    def handle(self, *args, **kwargs):
        if not CRYPTO_COMPARE_API_KEY:
            self.stdout.write(self.style.ERROR("❌ CRYPTO_COMPARE_API_KEY not found"))
            return

        headers = {"Authorization": f"Apikey {CRYPTO_COMPARE_API_KEY}"}

        for symbol, (cg_id, model) in COINS.items():
            self.stdout.write(f"\n🔄 Fetching {symbol} data...")

            try:
                # 1. Get hourly prices
                histo_url = "https://min-api.cryptocompare.com/data/v2/histohour"
                histo_params = {"fsym": symbol, "tsym": "USDT", "limit": 720}
                histo_res = requests.get(histo_url, headers=headers, params=histo_params)
                histo_data = histo_res.json()

                if histo_res.status_code != 200 or histo_data.get("Response") != "Success":
                    self.stdout.write(self.style.ERROR(f"❌ Histohour failed for {symbol}"))
                    continue

                hourly = histo_data["Data"]["Data"]

                # 2. Get market info
                market_url = "https://min-api.cryptocompare.com/data/pricemultifull"
                market_params = {"fsyms": symbol, "tsyms": "USDT"}
                market_res = requests.get(market_url, headers=headers, params=market_params)
                raw_data = market_res.json().get("RAW", {}).get(symbol, {}).get("USDT", {})

                market_cap = raw_data.get("MKTCAP")
                supply = raw_data.get("SUPPLY")
                max_supply = raw_data.get("MAXSUPPLY") or None
                circulating_supply = raw_data.get("CIRCULATINGSUPPLY")
                image_path = raw_data.get("IMAGEURL")
                image_url = f"https://www.cryptocompare.com{image_path}" if image_path else None

                # 3. Get description and percent changes from CoinGecko
                cg_url = f"https://api.coingecko.com/api/v3/coins/{cg_id}"
                cg_res = requests.get(cg_url)
                if cg_res.status_code != 200:
                    self.stdout.write(self.style.WARNING(f"⚠️ CoinGecko failed for {symbol}"))
                    continue

                cg_data = cg_res.json()
                description = cg_data.get("description", {}).get("en", "")
                percent_change_24h = cg_data.get("market_data", {}).get("price_change_percentage_24h")
                percent_change_7d = cg_data.get("market_data", {}).get("price_change_percentage_7d")

                # 4. Store entries
                entries = []
                for row in hourly:
                    t = timezone.make_aware(datetime.utcfromtimestamp(row["time"]))

                    if model.objects.filter(time=t).exists():
                        continue

                    entries.append(model(
                        time=t,
                        open_price=row.get("open"),
                        high_price=row.get("high"),
                        low_price=row.get("low"),
                        close_price=row.get("close"),
                        volume_from=row.get("volumefrom"),
                        volume_to=row.get("volumeto"),
                        market_cap=market_cap,
                        supply=supply,
                        max_supply=max_supply,
                        circulating_supply=circulating_supply,
                        image_url=image_url,
                        description=description,
                        percent_change_24h=percent_change_24h,
                        percent_change_7d=percent_change_7d,
                    ))

                if entries:
                    model.objects.bulk_create(entries, batch_size=500)
                    self.stdout.write(self.style.SUCCESS(
                        f"✅ {symbol}: {len(entries)} entries saved | 24h: {percent_change_24h:.2f}% | 7d: {percent_change_7d:.2f}%"
                    ))
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️ {symbol}: Already up to date"))

                time.sleep(1)  # Respect CoinGecko rate limit

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error for {symbol}: {str(e)}"))
