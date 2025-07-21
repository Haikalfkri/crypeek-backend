import requests
from django.core.management.base import BaseCommand
from api.models import CryptoSymbols

class Command(BaseCommand):
    help = "Import data crypto symbols dari Binance API ke database"

    def handle(self, *args, **kwargs):
        try:
            # Ambil data symbol dari Binance API
            url = "https://api.binance.com/api/v3/exchangeInfo"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            # Ambil semua trading pair yang aktif
            symbols = [
                s['symbol'] for s in data['symbols']
                if s['status'] == 'TRADING'
            ]
            
            # Hapus semua data sebelumnya agar tidak duplikat
            CryptoSymbols.objects.all().delete()

            # Masukkan setiap symbol ke dalam database
            for symbol in symbols:
                CryptoSymbols.objects.create(name=symbol)
            
            self.stdout.write(self.style.SUCCESS("Import data selesai. Semua symbol berhasil ditambahkan ke database."))

        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Terjadi kesalahan saat mengambil data dari Binance API: {e}"))
