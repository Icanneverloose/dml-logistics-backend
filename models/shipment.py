import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID

# Create a SQLAlchemy database instance (will be initialized in app.py)
db = SQLAlchemy()

class Shipment(db.Model):
    __tablename__ = 'shipments'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # Unique ID
    tracking_number = db.Column(db.String(64), unique=True, nullable=False)
    sender_name = db.Column(db.String(100), nullable=False)
    sender_email = db.Column(db.String(100), nullable=False)
    sender_phone = db.Column(db.String(20), nullable=False)
    sender_address = db.Column(db.String(200), nullable=False)
    receiver_name = db.Column(db.String(100), nullable=False)
    receiver_phone = db.Column(db.String(20), nullable=False)
    receiver_address = db.Column(db.String(200), nullable=False)
    package_type = db.Column(db.String(50), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    shipment_cost = db.Column(db.Float, nullable=False)
    date_registered = db.Column(db.DateTime, default=datetime.utcnow)
    estimated_delivery_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Registered')
    current_location = db.Column(db.String(200), nullable=True)  # Latest location from status updates
    pdf_url = db.Column(db.String(200), nullable=True)
    qr_url = db.Column(db.String(200), nullable=True)
    created_by = db.Column(db.String(100), nullable=True)  # User ID who created the shipment
    created_by_email = db.Column(db.String(100), nullable=True)  # Email of creator for easier filtering

    # Relationship to status logs
    status_logs = db.relationship('StatusLog', backref='shipment', lazy=True) 