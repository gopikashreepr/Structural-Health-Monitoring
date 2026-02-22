import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from __init__ import db
from models import SensorReading
from config import Config

logger = logging.getLogger(__name__)

class SensorService:
    """Service for handling sensor data operations"""
    
    @staticmethod
    def generate_sensor_data() -> Dict:
        """Generate realistic sensor data"""
        current_time = datetime.utcnow()
        
        # Add some realistic patterns and noise
        hour = current_time.hour
        
        # Temperature follows daily pattern
        temp_base = 25 + 10 * abs(hour - 12) / 12  # Higher at midday
        temperature = round(temp_base + random.uniform(-5, 5), 1)
        
        # Vibration with some correlation to temperature (thermal expansion)
        vibration_base = 0.5 + (temperature - 20) * 0.05
        vibration = round(max(0.1, vibration_base + random.uniform(-0.5, 1.5)), 2)
        
        # Strain with some randomness
        strain = round(random.uniform(0.0, 0.8), 3)
        
        return {
            'timestamp': current_time,
            'vibration': vibration,
            'strain': strain,
            'temperature': temperature
        }
    
    @staticmethod
    def save_reading(sensor_data: Dict) -> SensorReading:
        """Save sensor reading to database"""
        try:
            reading = SensorReading(
                timestamp=sensor_data['timestamp'],
                vibration=sensor_data['vibration'],
                strain=sensor_data['strain'],
                temperature=sensor_data['temperature']
            )
            
            db.session.add(reading)
            db.session.commit()
            
            logger.info(f"Saved sensor reading: {reading.id}")
            return reading
            
        except Exception as e:
            logger.error(f"Error saving sensor reading: {str(e)}")
            db.session.rollback()
            raise
    
    @staticmethod
    def get_readings(limit: int = 20) -> List[SensorReading]:
        """Get recent sensor readings"""
        try:
            return SensorReading.query.order_by(
                SensorReading.timestamp.desc()
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error fetching readings: {str(e)}")
            return []
    
    @staticmethod
    def get_readings_by_date_range(start_date: datetime, end_date: datetime) -> List[SensorReading]:
        """Get readings within date range"""
        try:
            return SensorReading.query.filter(
                SensorReading.timestamp >= start_date,
                SensorReading.timestamp <= end_date
            ).order_by(SensorReading.timestamp.desc()).all()
        except Exception as e:
            logger.error(f"Error fetching readings by date range: {str(e)}")
            return []
    
    @staticmethod
    def get_statistics() -> Dict:
        """Get basic statistics about sensor data"""
        try:
            # Get readings from last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            readings = SensorReading.query.filter(
                SensorReading.timestamp >= yesterday
            ).all()
            
            if not readings:
                return {
                    'total_readings': 0,
                    'anomalies': 0,
                    'alerts': 0,
                    'avg_temperature': 0,
                    'avg_vibration': 0,
                    'avg_strain': 0
                }
            
            # Calculate statistics
            total_readings = len(readings)
            anomalies = sum(1 for r in readings if r.is_anomaly)
            alerts = sum(1 for r in readings if r.alert_level != 'normal')
            
            avg_temperature = sum(r.temperature for r in readings) / total_readings
            avg_vibration = sum(r.vibration for r in readings) / total_readings
            avg_strain = sum(r.strain for r in readings) / total_readings
            
            return {
                'total_readings': total_readings,
                'anomalies': anomalies,
                'alerts': alerts,
                'avg_temperature': round(avg_temperature, 1),
                'avg_vibration': round(avg_vibration, 2),
                'avg_strain': round(avg_strain, 3)
            }
            
        except Exception as e:
            logger.error(f"Error calculating statistics: {str(e)}")
            return {
                'total_readings': 0,
                'anomalies': 0,
                'alerts': 0,
                'avg_temperature': 0,
                'avg_vibration': 0,
                'avg_strain': 0
            }
    
    @staticmethod
    def check_thresholds(reading: SensorReading) -> Tuple[str, List[str]]:
        """Check if reading exceeds thresholds"""
        thresholds = Config.ALERT_THRESHOLDS
        alert_level = 'normal'
        messages = []
        
        # Check each sensor type
        for sensor_type, limits in thresholds.items():
            value = getattr(reading, sensor_type)
            
            if value >= limits['critical']:
                alert_level = 'critical'
                messages.append(f"{sensor_type.title()} critical: {value} >= {limits['critical']}")
            elif value >= limits['warning'] and alert_level != 'critical':
                alert_level = 'warning'
                messages.append(f"{sensor_type.title()} warning: {value} >= {limits['warning']}")
        
        return alert_level, messages