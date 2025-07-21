import requests
import time
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from api.models import (
    BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, TONUSDT, ADAUSDT,
    DOGEUSDT, AVAXUSDT, LINKUSDT, DOTUSDT, MATICUSDT, ICPUSDT, LTCUSDT,
    SHIBUSDT, BCHUSDT, UNIUSDT, APTUSDT, NEARUSDT, XLMUSDT
)

symbol_to_model = {
    'BTCUSDT': BTCUSDT,
    'ETHUSDT': ETHUSDT,
    'BNBUSDT': BNBUSDT,
    'SOLUSDT': SOLUSDT,
    'XRPUSDT': XRPUSDT,
    'TONUSDT': TONUSDT,
    'ADAUSDT': ADAUSDT,
    'DOGEUSDT': DOGEUSDT,
    'AVAXUSDT': AVAXUSDT,
    'LINKUSDT': LINKUSDT,
    'DOTUSDT': DOTUSDT,
    'MATICUSDT': MATICUSDT,
    'ICPUSDT': ICPUSDT,
    'LTCUSDT': LTCUSDT,
    'SHIBUSDT': SHIBUSDT,
    'BCHUSDT': BCHUSDT,
    'UNIUSDT': UNIUSDT,
    'APTUSDT': APTUSDT,
    'NEARUSDT': NEARUSDT,
    'XLMUSDT': XLMUSDT,
}

class Command(BaseCommand):
    help = 'Fetch historical daily data for top 20 coins from Binance'

    def handle(self, *args, **kwargs):
        top_20_symbols = list(symbol_to_model.keys())

        for symbol in top_20_symbols:
            self.stdout.write(self.style.WARNING(f'Fetching {symbol}...'))
            model = symbol_to_model[symbol]

            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=5 * 365)).timestamp() * 1000)

            total_saved = 0

            while start_time < end_time:
                url = 'https://api.binance.com/api/v3/klines'
                params = {
                    'symbol': symbol,
                    'interval': '1d',
                    'startTime': start_time,
                    'limit': 1000
                }

                try:
                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()

                    if not data or isinstance(data, dict):
                        self.stdout.write(self.style.WARNING(f'No data returned for {symbol} at {start_time}'))
                        break

                    for candle in data:
                        ts = timezone.make_aware(datetime.fromtimestamp(candle[0] / 1000))
                        _, created = model.objects.update_or_create(
                            timestamp=ts,
                            defaults={
                                'open': float(candle[1]),
                                'high': float(candle[2]),
                                'low': float(candle[3]),
                                'close': float(candle[4]),
                                'volume': float(candle[5]),
                                'close_time': int(candle[6]),
                                'quote_asset_volume': float(candle[7]),
                                'num_trades': int(candle[8]),
                                'taker_buy_base_vol': float(candle[9]),
                                'taker_buy_quote_vol': float(candle[10]),
                            }
                        )
                        if created:
                            total_saved += 1

                    # Move to next batch
                    start_time = data[-1][0] + 86400000
                    time.sleep(0.2)

                except requests.exceptions.RequestException as e:
                    self.stdout.write(self.style.ERROR(f'Error fetching {symbol}: {e}'))
                    time.sleep(5)  # wait before retrying

            self.stdout.write(self.style.SUCCESS(f'{symbol} done: {total_saved} records saved or updated.'))
