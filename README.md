# weather-bot

## setup
```bash
source .env
python3.12 -m venv venv
source venv/bin/activate
pip install "pipecat-ai[daily,google,openai,silero]" noaa_sdk python-dotenv
```

## run

```bash
python weather-bot.py
```
or

```bash
DAILY_ROOM=https://my-domain.daily.co/room python weather-bot.py
```