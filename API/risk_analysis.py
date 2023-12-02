import json
import os
import random

from confluent_kafka import Consumer, KafkaError
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from API.db_models import Payment

load_dotenv()

engine = create_engine(os.getenv("POSTGRES_CONNECTION_STRING"))
DBSession = sessionmaker(bind=engine)
session = DBSession()


def perform_risk_analysis(payment: Payment):
    """
    Perform a basic risk analysis.
    Generate random number to be the risk and decide by it if the payment is risky.
    Update the DB with the risk and approval status.

    For simplicity, this function randomly approves 70% of payments.
    """
    risk_assessment = random.random()
    status = 'Approved' if risk_assessment <= 0.7 else 'Declined'

    payment_record = session.query(Payment).get(payment.id)
    payment_record.approval_status = status
    payment_record.risk_assessment = risk_assessment
    session.commit()

    print(f"Payment ID: {payment.id}, Status: {status}, Risk Assessment: {risk_assessment}")


def start_consumer():
    conf = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVER'),
        'group.id': 'my_consumer_group',
        'auto.offset.reset': 'earliest'
    }
    consumer = Consumer(conf)
    consumer.subscribe([os.getenv('KAFKA_TOPIC_NAME')])

    try:
        while True:
            msg = consumer.poll(1.0)

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"Error: {msg.error()}")
                    break

            data = json.loads(msg.value().decode('utf-8'))
            payments_instance: Payment = Payment(**data)
            perform_risk_analysis(payments_instance)

    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()


if __name__ == "__main__":
    start_consumer()
