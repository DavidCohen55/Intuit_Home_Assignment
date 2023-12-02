from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String, Float, Integer

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
        }


class Currency(db.Model):
    __tablename__ = 'currencies'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name
        }


class PaymentMethod(db.Model):
    __tablename__ = 'payment_methods'
    id = Column(String, primary_key=True)
    user_id = Column(String, db.ForeignKey('users.id'), nullable=False)
    payment_type = Column(String, nullable=False)
    payment_number = Column(String, unique=True, nullable=False)

    def serialize(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "payment_type": self.payment_type,
            "payment_number": self.payment_number
        }


class Payment(db.Model):
    __tablename__ = 'payments'
    id = Column(String, primary_key=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    user_id = Column(String, db.ForeignKey('users.id'), nullable=False)
    payee_id = Column(String, db.ForeignKey('users.id'), nullable=False)
    payment_methods_id = Column(String, db.ForeignKey('payment_methods.id'), nullable=False)
    approval_status = Column(String, nullable=False, default='Pending')
    risk_assessment = Column(Float, nullable=False)

    def __init__(self, id: str, amount: float, currency: str, user_id: str, payee_id: str, payment_methods_id: str,
                 approval_status: str = 'Pending', risk_assessment: float = None):
        self.id = id
        self.amount = amount
        self.currency = currency
        self.user_id = user_id
        self.payee_id = payee_id
        self.payment_methods_id = payment_methods_id
        self.approval_status = approval_status
        self.risk_assessment = risk_assessment

    def serialize(self):
        return {
            "id": self.id,
            "amount": self.amount,
            "currency": self.currency,
            "user_id": self.user_id,
            "payee_id": self.payee_id,
            "payment_methods_id": self.payment_methods_id,
            "approval_status": self.approval_status,
            "risk_assessment": self.risk_assessment
        }
