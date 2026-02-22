import pytest
import json
from datetime import datetime, timedelta
from app import app
from __init__ import db
from models import SensorReading, MLModel, AlertLog

@pytest.fixture
def client():
    """Create a test client"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Add some test data
            reading1 = SensorReading(
                vibration=1.5,
                strain=0.3,
                temperature=25.0,
                timestamp=datetime.utcnow() - timedelta(hours=1)
            )
            reading2 = SensorReading(
                vibration=2.5,
                strain=0.6,
                temperature=35.0,
                timestamp=datetime.utcnow(),
                is_anomaly=True,
                alert_level='warning'
            )
            db.session.add_all([reading1, reading2])
            db.session.commit()
            
        yield client

def test_dashboard_route(client):
    """Test the dashboard route"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Sensor Data Dashboard' in response.data

def test_healthcheck(client):
    """Test the healthcheck endpoint"""
    response = client.get('/healthcheck')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_sensor_data_endpoint(client):
    """Test the sensor data endpoint"""
    response = client.get('/sensor-data')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Check required fields
    assert 'vibration' in data
    assert 'strain' in data
    assert 'temperature' in data
    assert 'timestamp' in data
    assert 'is_anomaly' in data
    assert 'alert_level' in data
    
    # Check data types and ranges
    assert isinstance(data['vibration'], (int, float))
    assert isinstance(data['strain'], (int, float))
    assert isinstance(data['temperature'], (int, float))
    assert isinstance(data['is_anomaly'], bool)
    assert data['alert_level'] in ['normal', 'warning', 'critical']

def test_api_readings(client):
    """Test the API readings endpoint"""
    response = client.get('/api/readings')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'readings' in data
    assert 'total' in data
    assert len(data['readings']) > 0

def test_api_readings_with_filters(client):
    """Test API readings with filters"""
    response = client.get('/api/readings?anomalies_only=true')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # All readings should be anomalies
    for reading in data['readings']:
        assert reading['is_anomaly'] == True

def test_history_dashboard(client):
    """Test the history dashboard"""
    response = client.get('/history/')
    assert response.status_code == 200
    assert b'Historical Data Dashboard' in response.data

def test_history_data_endpoint(client):
    """Test the history data endpoint"""
    response = client.get('/history/data')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'readings' in data
    assert 'total' in data
    assert 'page' in data
    assert 'per_page' in data

def test_history_chart_data(client):
    """Test the history chart data endpoint"""
    response = client.get('/history/charts?period=day&days=7')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'labels' in data
    assert 'datasets' in data
    assert len(data['datasets']) == 3  # vibration, strain, temperature

def test_statistics_endpoint(client):
    """Test the statistics endpoint"""
    response = client.get('/statistics')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'sensor_stats' in data
    assert 'alert_stats' in data
    assert 'ml_stats' in data

def test_ml_model_info(client):
    """Test ML model info endpoint"""
    response = client.get('/api/ml/info')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Should return error if no model is loaded
    assert 'error' in data or 'model_name' in data

def test_alert_history(client):
    """Test alert history endpoint"""
    response = client.get('/api/alerts/history')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'alerts' in data
    assert 'total' in data

def test_export_data(client):
    """Test data export endpoint"""
    response = client.get('/history/export')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'

def test_sensor_reading_model():
    """Test SensorReading model"""
    reading = SensorReading(
        vibration=1.5,
        strain=0.3,
        temperature=25.0
    )
    
    assert reading.vibration == 1.5
    assert reading.strain == 0.3
    assert reading.temperature == 25.0
    assert reading.is_anomaly == False
    assert reading.alert_level == 'normal'

def test_sensor_reading_to_dict():
    """Test SensorReading to_dict method"""
    reading = SensorReading(
        vibration=1.5,
        strain=0.3,
        temperature=25.0,
        timestamp=datetime.utcnow()
    )
    
    data = reading.to_dict()
    assert 'vibration' in data
    assert 'strain' in data
    assert 'temperature' in data
    assert 'timestamp' in data
    assert 'is_anomaly' in data
    assert 'alert_level' in data

if __name__ == '__main__':
    pytest.main([__file__])