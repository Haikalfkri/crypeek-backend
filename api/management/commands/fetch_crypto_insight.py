import os
import re
import requests
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone
from django.core.management.base import BaseCommand
from api.models import CryptoInsight
from openai import OpenAI

import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)  # API key dari env OPENAI_API_KEY otomatis

class Command(BaseCommand):
    help = 'Fetch latest crypto insight news and classify them using OpenAI'

    VALID_CATEGORIES = {"BITCOIN", "ETHEREUM", "SOLANA", "ALTCOIN", "MULTICOIN", "GENERAL"}

    def classify_category(self, title, body):
        prompt = (
            "You're an assistant that classifies crypto news articles. "
            "Given the title and body of a news article, categorize it as one of:\n"
            "- BITCOIN\n- ETHEREUM\n- SOLANA\n- ALTCOIN\n- MULTICOIN\n- GENERAL (if unrelated to specific coin)\n\n"
            f"Title: {title}\n"
            f"Body: {body}\n"
            "Category:"
        )

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=15,
                temperature=0.2,
            )
            raw_output = response.choices[0].message.content.strip()
            print(f"[OpenAI RAW OUTPUT] {raw_output}")

            match = re.search(r"\b(BITCOIN|ETHEREUM|SOLANA|ALTCOIN|MULTICOIN|GENERAL)\b", raw_output.upper())
            if match:
                return match.group(1)
            return "GENERAL"
        except Exception as e:
            print(f"[OpenAI ERROR] {e}")
            return "GENERAL"

    def handle(self, *args, **kwargs):
        crypto_api_key = os.getenv('CRYPTOCOMPARE_API_KEY')
        url = f'https://min-api.cryptocompare.com/data/v2/news/?lang=EN&api_key={crypto_api_key}&limit=30'

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to fetch news: {e}"))
            return

        articles = data.get('Data', [])
        count = 0

        for article in articles:
            title = article.get('title', '').strip()
            body = article.get('body', '').strip()
            link = article.get('url', '').strip()
            source = article.get('source', '').strip() or 'Unknown'
            image_url = article.get('imageurl') or None

            if not title or not link:
                continue

            title = title[:255]
            link = link[:512]
            source = source[:255]

            published_on = article.get('published_on')
            try:
                if published_on:
                    naive_dt = datetime.utcfromtimestamp(published_on)
                    date = timezone.make_aware(naive_dt, dt_timezone.utc)
                else:
                    date = timezone.now()
            except Exception as e:
                self.stderr.write(f"Date parse error for article '{title[:40]}...': {e}")
                date = timezone.now()

            if CryptoInsight.objects.filter(title=title, link=link).exists():
                continue

            category = self.classify_category(title, body)

            CryptoInsight.objects.create(
                title=title,
                link=link,
                date=date,
                source=source,
                image=image_url,
                category=category
            )
            count += 1
            print(f"[SAVED] {title[:60]}... | Category: {category} | Date: {date.isoformat()}")

        self.stdout.write(self.style.SUCCESS(f'Successfully saved {count} new crypto insight articles.'))
