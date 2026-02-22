import logging
import json
import pickle
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
from __init__ import db
from models import SensorReading, MLModel
from config import Config

logger = logging.getLogger(__name__)

class MLService:
    """Service for machine learning operations"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.model_type = 'IsolationForest'
        
    def prepare_training_data(self, readings: List[SensorReading]) -> Tuple[np.ndarray, List[int]]:
        """Prepare data for training"""
        if not readings:
            return np.array([]), []
            
        # Extract features
        features = []
        reading_ids = []
        
        for reading in readings:
            features.append([
                reading.vibration,
                reading.strain,
                reading.temperature,
                reading.timestamp.hour,  # Time of day feature
                reading.timestamp.weekday()  # Day of week feature
            ])
            reading_ids.append(reading.id)
        
        return np.array(features), reading_ids
    
    def train_isolation_forest(self, contamination: float = 0.1) -> Dict:
        """Train Isolation Forest model"""
        try:
            # Get training data
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            readings = SensorReading.query.filter(
                SensorReading.timestamp >= cutoff_date
            ).order_by(SensorReading.timestamp.desc()).limit(
                Config.ML_TRAINING_DATA_SIZE
            ).all()
            
            if len(readings) < 50:
                logger.warning("Insufficient data for training")
                return {"error": "Insufficient training data"}
            
            features, reading_ids = self.prepare_training_data(readings)
            
            # Scale features
            self.scaler = StandardScaler()
            features_scaled = self.scaler.fit_transform(features)
            
            # Train model
            self.model = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=100
            )
            self.model.fit(features_scaled)
            
            # Make predictions on training data
            predictions = self.model.predict(features_scaled)
            anomaly_scores = self.model.decision_function(features_scaled)
            
            # Save model metadata
            model_record = MLModel(
                model_name=f"isolation_forest_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                model_type='IsolationForest',
                training_data_size=len(readings),
                model_params=json.dumps({
                    'contamination': contamination,
                    'n_estimators': 100,
                    'random_state': 42
                })
            )
            
            db.session.add(model_record)
            db.session.commit()
            
            logger.info(f"Trained Isolation Forest with {len(readings)} samples")
            
            return {
                "model_type": "IsolationForest",
                "training_samples": len(readings),
                "anomalies_detected": sum(1 for p in predictions if p == -1),
                "model_id": model_record.id
            }
            
        except Exception as e:
            logger.error(f"Error training Isolation Forest: {str(e)}")
            db.session.rollback()
            return {"error": str(e)}
    
    def train_one_class_svm(self, nu: float = 0.1) -> Dict:
        """Train One-Class SVM model"""
        try:
            # Get training data
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            readings = SensorReading.query.filter(
                SensorReading.timestamp >= cutoff_date
            ).order_by(SensorReading.timestamp.desc()).limit(
                Config.ML_TRAINING_DATA_SIZE
            ).all()
            
            if len(readings) < 50:
                logger.warning("Insufficient data for training")
                return {"error": "Insufficient training data"}
            
            features, reading_ids = self.prepare_training_data(readings)
            
            # Scale features
            self.scaler = StandardScaler()
            features_scaled = self.scaler.fit_transform(features)
            
            # Train model
            self.model = OneClassSVM(
                nu=nu,
                kernel='rbf',
                gamma='scale'
            )
            self.model.fit(features_scaled)
            
            # Make predictions on training data
            predictions = self.model.predict(features_scaled)
            anomaly_scores = self.model.decision_function(features_scaled)
            
            # Save model metadata
            model_record = MLModel(
                model_name=f"one_class_svm_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                model_type='OneClassSVM',
                training_data_size=len(readings),
                model_params=json.dumps({
                    'nu': nu,
                    'kernel': 'rbf',
                    'gamma': 'scale'
                })
            )
            
            db.session.add(model_record)
            db.session.commit()
            
            logger.info(f"Trained One-Class SVM with {len(readings)} samples")
            
            return {
                "model_type": "OneClassSVM",
                "training_samples": len(readings),
                "anomalies_detected": sum(1 for p in predictions if p == -1),
                "model_id": model_record.id
            }
            
        except Exception as e:
            logger.error(f"Error training One-Class SVM: {str(e)}")
            db.session.rollback()
            return {"error": str(e)}
    
    def predict_anomaly(self, reading: SensorReading) -> Tuple[bool, float]:
        """Predict if reading is anomalous"""
        if not self.model or not self.scaler:
            # Try to train model if not available
            result = self.train_isolation_forest()
            if "error" in result:
                logger.warning("Could not train model for prediction")
                return False, 0.0
        
        try:
            # Prepare features
            features = np.array([[
                reading.vibration,
                reading.strain,
                reading.temperature,
                reading.timestamp.hour,
                reading.timestamp.weekday()
            ]])
            
            # Scale features
            features_scaled = self.scaler.transform(features)
            
            # Make prediction
            prediction = self.model.predict(features_scaled)[0]
            score = self.model.decision_function(features_scaled)[0]
            
            is_anomaly = prediction == -1
            
            return is_anomaly, float(score)
            
        except Exception as e:
            logger.error(f"Error predicting anomaly: {str(e)}")
            return False, 0.0
    
    def update_reading_with_prediction(self, reading: SensorReading) -> SensorReading:
        """Update reading with ML prediction"""
        try:
            is_anomaly, score = self.predict_anomaly(reading)
            
            reading.is_anomaly = is_anomaly
            reading.anomaly_score = score
            
            db.session.commit()
            
            logger.info(f"Updated reading {reading.id} with anomaly prediction: {is_anomaly}")
            
            return reading
            
        except Exception as e:
            logger.error(f"Error updating reading with prediction: {str(e)}")
            db.session.rollback()
            return reading
    
    def get_model_info(self) -> Dict:
        """Get information about current model"""
        if not self.model:
            return {"error": "No model loaded"}
        
        try:
            latest_model = MLModel.query.filter_by(
                model_type=self.model_type,
                is_active=True
            ).order_by(MLModel.created_at.desc()).first()
            
            if latest_model:
                return latest_model.to_dict()
            else:
                return {"error": "No model metadata found"}
                
        except Exception as e:
            logger.error(f"Error getting model info: {str(e)}")
            return {"error": str(e)}
    
    def retrain_if_needed(self) -> Dict:
        """Retrain model if needed based on time interval"""
        try:
            latest_model = MLModel.query.filter_by(
                model_type=self.model_type,
                is_active=True
            ).order_by(MLModel.created_at.desc()).first()
            
            if not latest_model:
                logger.info("No existing model found, training new one")
                return self.train_isolation_forest()
            
            # Check if model is old enough to retrain
            age = datetime.utcnow() - latest_model.created_at
            if age > Config.ML_MODEL_RETRAIN_INTERVAL:
                logger.info(f"Model is {age} old, retraining")
                
                # Deactivate old model
                latest_model.is_active = False
                db.session.commit()
                
                return self.train_isolation_forest()
            
            return {"message": "Model is up to date"}
            
        except Exception as e:
            logger.error(f"Error checking retrain schedule: {str(e)}")
            return {"error": str(e)}