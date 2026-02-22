from datetime import datetime
from __init__ import db
from sqlalchemy import Index

class SensorReading(db.Model):
    """Model for storing sensor readings"""
    __tablename__ = 'sensor_readings'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    vibration = db.Column(db.Float, nullable=False)
    strain = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    
    # ML prediction results
    is_anomaly = db.Column(db.Boolean, default=False)
    anomaly_score = db.Column(db.Float, default=0.0)
    
    # Alert information
    alert_level = db.Column(db.String(20), default='normal')  # normal, warning, critical
    alert_sent = db.Column(db.Boolean, default=False)
    
    # Add indexes for better query performance
    __table_args__ = (
        Index('ix_sensor_readings_timestamp', 'timestamp'),
        Index('ix_sensor_readings_alert_level', 'alert_level'),
        Index('ix_sensor_readings_is_anomaly', 'is_anomaly'),
    )
    
    def __repr__(self):
        return f'<SensorReading {self.id}: {self.timestamp}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'vibration': self.vibration,
            'strain': self.strain,
            'temperature': self.temperature,
            'is_anomaly': self.is_anomaly,
            'anomaly_score': self.anomaly_score,
            'alert_level': self.alert_level,
            'alert_sent': self.alert_sent
        }
    
    @classmethod
    def get_latest(cls, limit=20):
        """Get the latest sensor readings"""
        return cls.query.order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def get_by_date_range(cls, start_date, end_date):
        """Get readings within a date range"""
        return cls.query.filter(
            cls.timestamp >= start_date,
            cls.timestamp <= end_date
        ).order_by(cls.timestamp.desc()).all()
    
    @classmethod
    def get_anomalies(cls, limit=50):
        """Get anomalous readings"""
        return cls.query.filter(cls.is_anomaly == True).order_by(
            cls.timestamp.desc()
        ).limit(limit).all()
    
    @classmethod
    def get_alerts(cls, alert_level='warning', limit=50):
        """Get readings with specific alert level"""
        return cls.query.filter(cls.alert_level == alert_level).order_by(
            cls.timestamp.desc()
        ).limit(limit).all()

class MLModel(db.Model):
    """Model for storing ML model metadata"""
    __tablename__ = 'ml_models'
    
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)
    model_type = db.Column(db.String(50), nullable=False)  # e.g., 'IsolationForest'
    training_data_size = db.Column(db.Integer, nullable=False)
    accuracy_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Store model parameters as JSON
    model_params = db.Column(db.Text)  # JSON string of model parameters
    
    def __repr__(self):
        return f'<MLModel {self.model_name}: {self.model_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'model_name': self.model_name,
            'model_type': self.model_type,
            'training_data_size': self.training_data_size,
            'accuracy_score': self.accuracy_score,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }

class AlertLog(db.Model):
    """Model for logging alerts sent"""
    __tablename__ = 'alert_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    reading_id = db.Column(db.Integer, db.ForeignKey('sensor_readings.id'), nullable=False)
    alert_type = db.Column(db.String(20), nullable=False)  # email, sms
    alert_level = db.Column(db.String(20), nullable=False)  # warning, critical
    recipient = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)
    
    # Relationship
    reading = db.relationship('SensorReading', backref='alert_logs')
    
    def __repr__(self):
        return f'<AlertLog {self.id}: {self.alert_type} to {self.recipient}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'reading_id': self.reading_id,
            'alert_type': self.alert_type,
            'alert_level': self.alert_level,
            'recipient': self.recipient,
            'message': self.message,
            'sent_at': self.sent_at.isoformat(),
            'success': self.success,
            'error_message': self.error_message
        }