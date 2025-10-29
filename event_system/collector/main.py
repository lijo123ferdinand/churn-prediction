from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from confluent_kafka import Producer
import json

app = FastAPI()
print("Starting FastAPI collector...")

@app.on_event("startup")
async def startup_event():
    print("Collector startup: routes registered")

# CORS middleware — allows React frontend on localhost:3003
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3003"],  # for testing you can use ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kafka producer
producer = Producer({'bootstrap.servers': 'kafka:9092'})
TOPIC = 'user_events'

# Root GET route — sanity check
@app.get("/")
async def root():
    return {"status": "running"}
@app.get("/test")
async def test():
    print("GET /test called")
    return {"message": "test route working"}

# POST /collect route — single or batch events
@app.post("/collect")
async def collect_event(request: Request):
    try:
        events = await request.json()
        if isinstance(events, dict):
            events = [events]
        for event in events:
            producer.produce(TOPIC, json.dumps(event).encode('utf-8'))
        producer.flush()
        return {"status": "ok", "count": len(events)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
