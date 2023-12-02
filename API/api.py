import json
import os
import uuid
from typing import Tuple

from confluent_kafka import Producer
from dotenv import load_dotenv
from faker import Faker
from flask import Flask, request, jsonify

from db_models import Payment, PaymentMethod, User, Currency
from db_models import db

# Load environment variables from the .env file
load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("POSTGRES_CONNECTION_STRING")

kafka_config = {
    'bootstrap.servers': os.getenv("KAFKA_BOOTSTRAP_SERVER"),
    'client.id': 'flask-payment-api'
}

producer = Producer(kafka_config)


@app.route('/payment_methods', methods=['GET'])
def get_payment_methods():
    """
    Retrieve a list of payment methods.

    Parameters: None

    Status Codes:
    - 200 OK: Successful request.
    - 500 Internal Server Error: An error occurred on the server.

    Result: A JSON array containing serialized payment methods.
    """
    payment_methods = PaymentMethod.query.all()
    return [payment_method.serialize() for payment_method in payment_methods]


@app.route('/payees', methods=['GET'])
def get_payees():
    """
    Retrieve a list of payees.

    Parameters: None

    Status Codes:
    - 200 OK: Successful request.
    - 500 Internal Server Error: An error occurred on the server.

    Result: A JSON array containing serialized payees.
    """
    payees = User.query.all()
    return [payee.serialize() for payee in payees]


def __validate_payment_request(data: dict) -> Tuple[str, int]:
    """
    Validate a payment request.

    Parameters:
    - data (dict): A dictionary containing payment request data.
        - Required fields: ['amount', 'currency', 'userId', 'payeeId', 'paymentMethodId']

    Returns:
    - Tuple[str, int]: A tuple containing the result message and the HTTP status code.
        - If validation is successful, the message is 'Validation successful' and the status code is 200.
        - If there is an error, the message is an error description, and the status code indicates the HTTP error.
            - 400 Bad Request: Missing required fields or illegal amount.
            - 400 Bad Request: Attempt to move money between the same account.
            - 400 Bad Request: Invalid payment method.
            - 404 Not Found: User not found.
            - 404 User_id does not have payment_method_id

    """
    required_fields = ['amount', 'currency', 'userId', 'payeeId', 'paymentMethodId']

    if not all(field in data for field in required_fields):
        return 'Missing required fields', 400

    amount = data['amount']
    user_id = data['userId']
    payee_id = data['payeeId']
    payment_method_id = data['paymentMethodId']

    if amount <= 0:
        return 'Illegal amount, must be greater than 0', 400

    if payee_id == user_id:
        return 'Cannot move money between the same account', 400

    user = db.session.query(User).get(user_id)
    if not user:
        return f'User with ID {user_id} not found', 404

    payment_method = db.session.query(PaymentMethod).get(payment_method_id)
    if not payment_method:
        return 'Invalid payment method', 400

    if not db.session.query(PaymentMethod).filter_by(id=payment_method_id, user_id=user_id).first():
        return f'User with ID {user_id} does not have payment method with ID {payment_method_id}', 404

    payee = db.session.query(User).get(payee_id)
    if not payee:
        return f'Payee with ID {payee_id} not found', 404

    return 'Validation successful', 200


@app.route('/create_payment', methods=['POST'])
def create_payment():
    """
    Create a new payment.

    Parameters:
    - amount (float): The amount of the payment.
    - currency (str): The currency of the payment.
    - userId (str): The ID of the user initiating the payment.
    - payeeId (str): The ID of the payee (user receiving the payment).
    - paymentMethodId (str): The ID of the payment method to be used.

    Status Codes:
    - 201 Created: Payment successfully created.
    - 400 Bad Request: Missing required fields or illegal amount.
    - 400 Bad Request: Attempt to move money between the same account.
    - 400 Bad Request: Invalid payment method.
    - 404 Not Found: User not found.
    - 404 User_id does not have payment_method_id.

    Result: A JSON message indicating the status of the payment creation.
    """
    data = request.get_json()

    validation_result, status_code = __validate_payment_request(data)
    if status_code != 200:
        return jsonify({'error': validation_result}), status_code

    payment = Payment(
        id=str(uuid.uuid4()),
        amount=data['amount'],
        currency=data['currency'],
        user_id=data['userId'],
        payee_id=data['payeeId'],
        payment_methods_id=data['paymentMethodId']
    )

    try:
        producer.produce(os.getenv("KAFKA_TOPIC_NAME"), key=None, value=json.dumps(payment.serialize()))
        producer.flush()

        db.session.add(payment)
        db.session.commit()

        return jsonify({'message': 'Payment created successfully'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to write to Kafka: {str(e)}'}), 500


def __init_and_populate_db():
    """
    Create tables in DB according to ORM and populate the tables
    """
    with app.app_context():
        db.create_all()
        fake = Faker()
        for i in range(5):
            user_details = {
                "id": str(uuid.uuid4()),
                "name": fake.name(),
                "email": fake.email(),
                "card_number": fake.credit_card_number(card_type='amex')
            }

            db.session.add(User(id=user_details["id"], name=user_details["name"], email=user_details["email"]))
            db.session.commit()

            db.session.add(Currency(id=str(uuid.uuid4()), name=fake.currency_code()))
            db.session.add(PaymentMethod(
                id=str(uuid.uuid4()),
                user_id=user_details["id"],
                payment_type="AMEX",
                payment_number=user_details["card_number"]))
            db.session.commit()


def initialize_db(first_run: bool):
    db.init_app(app)

    if first_run:
        __init_and_populate_db()


if __name__ == '__main__':
    initialize_db(False)
    app.run(debug=True)
