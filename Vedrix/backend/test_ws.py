import asyncio
import websockets
import json

async def test_interview():
    uri = "ws://localhost:8000/api/v1/interview/ws/test123"
    print(f"Connecting to {uri}")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Waiting for first question...")
            
            # 1. Expect initial question
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                print(f"[RECV] type: {data.get('type')}")
                if data.get('type') == 'question':
                    print(f"   Question: {data['data']['question']}")
                    break
                elif data.get('type') == 'error':
                    print(f"   Error: {data['data']}")
                    return
            
            # 2. Send answer
            print("\nSending answer...")
            answer = {"type": "answer", "data": "I have experience with Python and FastAPI for backend development."}
            await websocket.send(json.dumps(answer))
            
            # 3. Expect status updates and next question or metrics
            for _ in range(5):
                response = await websocket.recv()
                data = json.loads(response)
                print(f"[RECV] type: {data.get('type')}")
                if data.get('type') == 'status':
                    print(f"   Status: {data['data']}")
                elif data.get('type') == 'metrics_update':
                    print(f"   Metrics: {data['data']}")
                elif data.get('type') == 'question':
                    print(f"   Next Question: {data['data']['question']}")
                    break
                elif data.get('type') == 'error':
                    print(f"   Error: {data['data']}")
                    break
            
            print("\nTest completed successfully.")
            
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_interview())
