import aiohttp
import asyncio
import os
import sys

from loguru import logger
from dotenv import load_dotenv

from noaa_sdk import NOAA

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import EndFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.gemini_multimodal_live.gemini import GeminiMultimodalLiveLLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper, DailyRoomParams

logger.remove(0)
logger.add(sys.stderr, level="DEBUG", colorize=True)
load_dotenv()
new_level_symbol = ".  ⛅︎  ."
new_level = logger.level(new_level_symbol, no=38, color="<light-magenta><BLACK>")

# webrtc room to talk to the bot
async def get_daily_room():
    room_override = os.getenv("DAILY_ROOM")
    if room_override:
        return room_override
    else:
        async with aiohttp.ClientSession() as session:
            daily_rest_helper = DailyRESTHelper(
                daily_api_key=os.getenv("DAILY_API_KEY"),
                daily_api_url=os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
                aiohttp_session=session,
            )

            room_config = await daily_rest_helper.create_room(
                DailyRoomParams(
                    properties={"enable_prejoin_ui":False}
                )
            )
            return room_config.url

# rest API call to NOAA to get current weather
async def get_noaa_simple_weather(latitude: float, longitude: float, **kwargs):
    n = NOAA()
    description = False
    fahrenheit_temp = 0
    try:
        observations = n.get_observations_by_lat_lon(latitude, longitude, num_of_stations=1)
        for observation in observations:
            description = observation["textDescription"]
            celsius_temp = observation["temperature"]["value"]
            if description:
                break

        fahrenheit_temp = (celsius_temp * 9 / 5) + 32

    except Exception as e:
        logger.log(new_level_symbol, f"Error getting NOAA weather: {e}")

    logger.log(new_level_symbol, f"get_noaa_simple_weather * results: {description}, {fahrenheit_temp}")
    return description, fahrenheit_temp

async def main():
    bot_name = "⛅︎ current  w e a t h e r  bot ⛅︎"
    room_url = await get_daily_room()

    # yes, it was worth the time to do this
    logger.opt(colors=True).log(new_level_symbol, f"<black><RED>_____*</RED></black>")
    logger.opt(colors=True).log(new_level_symbol, f"<black><LIGHT-RED>_____*</LIGHT-RED></black>")
    logger.opt(colors=True).log(new_level_symbol, f"<black><Y>_____*</Y></black>")
    logger.opt(colors=True).log(new_level_symbol, f"<black><G>_____*</G></black> Navigate to")
    logger.opt(colors=True).log(new_level_symbol, f"<black><C>_____*</C></black> <u><light-cyan>{room_url}</light-cyan></u>")
    logger.opt(colors=True).log(new_level_symbol, f"<black><E>_____*</E></black> to talk to")
    logger.opt(colors=True).log(new_level_symbol, f"<black><LIGHT-BLUE>_____*</LIGHT-BLUE></black> <light-blue>{bot_name}</light-blue>")
    logger.opt(colors=True).log(new_level_symbol, f"<black><MAGENTA>_____*</MAGENTA></black>")
    logger.opt(colors=True).log(new_level_symbol, f"<black><R>_____*</R></black>")

    transport = DailyTransport(
        room_url,
        None,
        bot_name,
        DailyParams(
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000,
            audio_out_enabled=True,
            vad_enabled=True,
            vad_audio_passthrough=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.5)),
        ),
    )

    system_instruction = """
    You are a helpful assistant who can answer questions and use tools.

    You have a tool called "get_weather" that can be used to get the current weather.

    If the user asks for the weather, call this tool and do not ask the user for latitude and longitude. 
    Infer latitude and longitude from the location and use those in the get_weather tool. 
    Use ONLY this tool to get weather information. Never use other tools or apis, even if you encounter an error.
    Say you are having trouble retrieving the weather if the tool call does not work.
    
    If you are asked about a location outside the United States, politely respond that you are only able to retrieve current weather information for locations in the United States. 
    If a location is not provided, always ask the user what location for which they would like the weather.
    """

    tools = [
        {
            "function_declarations": [
                {
                    "name": "get_weather",
                    "description": "Get the current weather",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The location for the weather request.",
                            },
                            "latitude": {
                                "type": "string",
                                "description": "Provide this by infering the latitude from the location. Supply latitude as a string. For example, '42.3601'.",
                            },
                            "longitude": {
                                "type": "string",
                                "description": "Provide this by infering the longitude from the location. Supply longitude as a string. For example, '-71.0589'.",
                            },
                        },
                        "required": ["location", "latitude", "longitude"],
                    },
                },
            ]
        }
    ]

    llm = GeminiMultimodalLiveLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        system_instruction=system_instruction,
        tools=tools,
    )

    async def fetch_weather_from_api(
        function_name, tool_call_id, args, llm, context, result_callback
    ):
        location = args["location"]
        latitude = float(args["latitude"])
        longitude = float(args["longitude"])
        description, fahrenheit_temp = None, None

        logger.log(new_level_symbol, f"fetch_weather_from_api * location: {location} - '{latitude}, {longitude}'")

        if latitude and longitude:
            # actual external rest API call
            description, fahrenheit_temp = await get_noaa_simple_weather(latitude, longitude)
        else:
            return await result_callback("Sorry, I don't recognize that location.")

        if not fahrenheit_temp:
            return await result_callback(
                f"I'm sorry, I can't get the weather for {location} right now. Can you ask again please?"
            )

        if not description:
            return await result_callback(
                f"According to noah, the weather in {location} is currently {round(fahrenheit_temp)} degrees."
            )
        else:
            return await result_callback(
                f"According to noah, the weather in {location} is currently {round(fahrenheit_temp)} degrees and {description}."
            )

    llm.register_function("get_weather", fetch_weather_from_api)

    # continue to setup pipeline
    context = OpenAILLMContext(
        [{"role": "user", "content": "Say hello. Make a subtle weather pun."}],
    )
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),               # Transport user input
            context_aggregator.user(),       # User responses
            llm,                             # LLM
            transport.output(),              # Transport bot output
            context_aggregator.assistant(),  # Assistant spoken responses
        ]
    )

    task = PipelineTask(
        pipeline,
        PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
        ),
    )

    # set event handlers
    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.log(new_level_symbol, f"Participant left: {participant}")
        await task.queue_frame(EndFrame())

    runner = PipelineRunner()

    await runner.run(task)

if __name__ == "__main__":
    asyncio.run(main())
