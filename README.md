# weather-bot

A weather bot is the 'hello world' of LLM function calling. I've found the documentation for most function calling / tool calling to gloss over any actual API calls made. (I call peanut butter on it always being 75 and sunny in NYC). So here is a tool calling 'hello world' that _actually_ calls an API. Shout out to [NOAA](https://www.noaa.gov/) for providing API access without a key, which makes running this example _a breeze_.* And thanks to the [Pipecat AI](https://github.com/pipecat-ai/pipecat) framework, it's all done in ~200 lines of code. Lastly but not leastly, Gemini Multimodal Live is really fast and cool.

## dependencies
Get a few free keys.

- Daily API Key
1. Signup at [Daily](https://dashboard.daily.co/u/signup?pipecat=y).
2. Verify email address and choose a subdomain to complete onboarding.
3. Click on "Developers" in left-side menu of Daily dashboard to reveal API Key.

- Gemini API key
1. Obtain that [here](https://aistudio.google.com/apikey).

## setup
```bash
cp env.example .env
# add Daily and Gemini keys
source .env
python3.12 -m venv venv
source venv/bin/activate
pip install "pipecat-ai[daily,google,openai,silero]" noaa_sdk python-dotenv
```

## run
```bash
python weather-bot.py
```
or, if you have a Daily room already created:

```bash
DAILY_ROOM=https://my-domain.daily.co/room python weather-bot.py
```

## profit

Not really. But this demo could be updated and totally used for profit.

* yes, that was a weather joke.