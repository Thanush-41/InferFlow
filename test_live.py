import asyncio
import httpx
import json

BASE = "http://localhost:8001"

async def test_all():
    async with httpx.AsyncClient(timeout=30) as client:

        # 1. Health
        r = await client.get(f"{BASE}/health")
        print(f"[1] Health: {r.json()}")

        # 2. Chat (non-streaming)
        r = await client.post(f"{BASE}/api/chat/send", json={
            "message": "What is 2+2? Answer in one word.",
            "model": "gemini-2.5-flash",
            "provider": "gemini",
            "stream": False
        })
        data = r.json()
        conv_id = data["conversation_id"]
        print(f"[2] Chat response: {data['message']['content']}")
        print(f"    Conversation ID: {conv_id}")

        # 3. Multi-turn
        r = await client.post(f"{BASE}/api/chat/send", json={
            "message": "What was my previous question?",
            "conversation_id": conv_id,
            "model": "gemini-2.5-flash",
            "provider": "gemini",
            "stream": False
        })
        print(f"[3] Multi-turn: {r.json()['message']['content']}")

        # 4. Streaming
        print("[4] Streaming: ", end="", flush=True)
        stream_conv_id = None
        async with client.stream("POST", f"{BASE}/api/chat/send/stream", json={
            "message": "Count to 3.",
            "model": "gemini-2.5-flash",
            "provider": "gemini",
            "stream": True
        }) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    chunk = json.loads(line[6:])
                    if chunk.get("content"):
                        print(chunk["content"], end="", flush=True)
                    if chunk.get("done"):
                        stream_conv_id = chunk.get("conversation_id")
        print()

        # 5. List conversations
        r = await client.get(f"{BASE}/api/conversations/")
        convs = r.json()
        print(f"[5] Conversations: {len(convs)} found")
        for c in convs:
            print(f"    - {c['id'][:8]}... | {c['status']} | {c['message_count']} msgs | {c['title']}")

        # 6. Get conversation
        r = await client.get(f"{BASE}/api/conversations/{conv_id}")
        conv = r.json()
        print(f"[6] Get conversation: {len(conv['messages'])} messages")

        # 7. Cancel conversation
        r = await client.post(f"{BASE}/api/conversations/{conv_id}/cancel")
        print(f"[7] Cancel: {r.json()}")

        # 8. Resume conversation
        r = await client.post(f"{BASE}/api/conversations/{conv_id}/resume")
        print(f"[8] Resume: {r.json()}")

        # 9. Queue status
        r = await client.get(f"{BASE}/api/ingest/queue/status")
        print(f"[9] Queue depth: {r.json()}")

        # 10. Dashboard metrics
        r = await client.get(f"{BASE}/api/dashboard/metrics?hours=1")
        print(f"[10] Dashboard metrics: {r.json()}")

        # 11. Provider stats
        r = await client.get(f"{BASE}/api/dashboard/providers?hours=1")
        print(f"[11] Provider stats: {r.json()}")

        # 12. Check via nginx proxy
        r = await client.get("http://localhost:8090/health")
        print(f"[12] Nginx proxy health: {r.json()}")

        print("\n✅ All live tests passed!")

asyncio.run(test_all())
