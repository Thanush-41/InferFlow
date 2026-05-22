import asyncio
from google import genai
from google.genai import types

API_KEY = "AIzaSyCjz_xNTFBrVUH1pDx1q6jokq1EOpRt-mo"

async def test_basic():
    print("=== Test 1: Basic generation ===")
    client = genai.Client(api_key=API_KEY)
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say hello in one sentence."
    )
    print("Response:", response.text)
    print("Tokens:", response.usage_metadata)

async def test_stream():
    print("\n=== Test 2: Streaming ===")
    client = genai.Client(api_key=API_KEY)
    full = []
    stream = await client.aio.models.generate_content_stream(
        model="gemini-2.5-flash",
        contents="Count from 1 to 5."
    )
    async for chunk in stream:
        if chunk.text:
            full.append(chunk.text)
            print(chunk.text, end="", flush=True)
    print("\nFull streamed:", "".join(full))

async def test_multiturn():
    print("\n=== Test 3: Multi-turn ===")
    client = genai.Client(api_key=API_KEY)
    contents = [
        types.Content(role="user", parts=[types.Part(text="My name is Alice.")]),
        types.Content(role="model", parts=[types.Part(text="Nice to meet you, Alice!")]),
        types.Content(role="user", parts=[types.Part(text="What is my name?")]),
    ]
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(system_instruction="You are a helpful assistant.")
    )
    print("Response:", response.text)

async def main():
    try:
        await test_basic()
        await test_stream()
        await test_multiturn()
        print("\n✅ All Gemini API tests passed!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(main())
