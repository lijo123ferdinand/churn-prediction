from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from confluent_kafka import Producer
import json

app = FastAPI()
print("Starting FastAPI collector...")

@app.on_event("startup")
async def startup_event():
    print("Collector startup: routes registered")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

producer = Producer({'bootstrap.servers': 'localhost:9092'})

USER_TOPIC = 'user_events'
CART_TOPIC = 'cart_events'


@app.get("/")
async def root():
    return {"status": "running"}


@app.post("/collect")
async def collect_event(request: Request):
    try:
        events = await request.json()

        if isinstance(events, dict):
            events = [events]

        for event in events:
            event_name = event.get("event_name", "")

            # ----------------------------
            # Routing Logic
            # ----------------------------
            if event_name in ["add_to_cart", "remove_from_cart", "update_quantity", "checkout", "view_cart"]:
                topic = CART_TOPIC
            else:
                topic = USER_TOPIC

            producer.produce(topic, json.dumps(event).encode("utf-8"))
            print(f"📤 Sent event to {topic}: {event_name}")

        producer.flush()
        return {"status": "ok", "count": len(events)}

    except Exception as e:
        return {"status": "error", "detail": str(e)}
