from confluent_kafka import Consumer
import json

consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'churn-predictor',
    'auto.offset.reset': 'earliest'
})

consumer.subscribe(['user_events'])

while True:
    msg = consumer.poll(1.0)
    if msg is None or msg.error():
        continue
    event = json.loads(msg.value().decode('utf-8'))
    print("Received event:", event)

    # Here you can call your churn prediction function
    # churn_risk = predict_churn(event)
    # print(f"User {event['user_id']} churn risk: {churn_risk}")
