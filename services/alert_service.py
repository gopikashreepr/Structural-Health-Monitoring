import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from flask import current_app
from flask_mail import Message
from twilio.rest import Client
from __init__ import db, mail
from models import SensorReading, AlertLog
from config import Config

logger = logging.getLogger(__name__)

class AlertService:
    """Service for handling alerts and notifications"""
    
    def __init__(self):
        self.twilio_client = None
        self._init_twilio()
    
    def _init_twilio(self):
        """Initialize Twilio client if credentials are available"""
        try:
            if current_app.config.get('TWILIO_ACCOUNT_SID') and current_app.config.get('TWILIO_AUTH_TOKEN'):
                self.twilio_client = Client(
                    current_app.config['TWILIO_ACCOUNT_SID'],
                    current_app.config['TWILIO_AUTH_TOKEN']
                )
                logger.info("Twilio client initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize Twilio client: {str(e)}")
    
    def send_email_alert(self, reading: SensorReading, alert_level: str, messages: List[str], recipient: str) -> Dict:
        """Send email alert"""
        try:
            if not current_app.config.get('MAIL_USERNAME'):
                logger.warning("Email not configured, skipping email alert")
                return {"error": "Email not configured"}
            
            subject = f"SHM Alert - {alert_level.upper()}"
            
            body = f"""
            Structural Health Monitoring Alert
            
            Alert Level: {alert_level.upper()}
            Timestamp: {reading.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
            
            Sensor Readings:
            - Vibration: {reading.vibration}
            - Strain: {reading.strain}
            - Temperature: {reading.temperature}°C
            
            Alert Messages:
            {chr(10).join(f"• {msg}" for msg in messages)}
            
            Anomaly Detection:
            - Is Anomaly: {reading.is_anomaly}
            - Anomaly Score: {reading.anomaly_score:.3f}
            
            Please investigate immediately.
            
            ---
            SHM System
            """
            
            msg = Message(
                subject=subject,
                sender=current_app.config['MAIL_USERNAME'],
                recipients=[recipient],
                body=body
            )
            
            mail.send(msg)
            
            # Log the alert
            self._log_alert(reading.id, 'email', alert_level, recipient, body, True)
            
            logger.info(f"Email alert sent to {recipient}")
            return {"success": True, "message": "Email sent successfully"}
            
        except Exception as e:
            error_msg = f"Error sending email alert: {str(e)}"
            logger.error(error_msg)
            
            # Log the failed alert
            self._log_alert(reading.id, 'email', alert_level, recipient, "", False, error_msg)
            
            return {"error": error_msg}
    
    def send_sms_alert(self, reading: SensorReading, alert_level: str, messages: List[str], recipient: str) -> Dict:
        """Send SMS alert"""
        try:
            if not self.twilio_client:
                logger.warning("Twilio not configured, skipping SMS alert")
                return {"error": "Twilio not configured"}
            
            # Create concise SMS message
            body = f"SHM {alert_level.upper()} ALERT at {reading.timestamp.strftime('%H:%M')}: "
            body += f"V:{reading.vibration} S:{reading.strain} T:{reading.temperature}°C"
            
            if messages:
                body += f" - {messages[0]}"  # Include first alert message
            
            message = self.twilio_client.messages.create(
                body=body,
                from_=current_app.config['TWILIO_PHONE_NUMBER'],
                to=recipient
            )
            
            # Log the alert
            self._log_alert(reading.id, 'sms', alert_level, recipient, body, True)
            
            logger.info(f"SMS alert sent to {recipient}, SID: {message.sid}")
            return {"success": True, "message": "SMS sent successfully", "sid": message.sid}
            
        except Exception as e:
            error_msg = f"Error sending SMS alert: {str(e)}"
            logger.error(error_msg)
            
            # Log the failed alert
            self._log_alert(reading.id, 'sms', alert_level, recipient, "", False, error_msg)
            
            return {"error": error_msg}
    
    def _log_alert(self, reading_id: int, alert_type: str, alert_level: str, 
                   recipient: str, message: str, success: bool, error_message: str = None):
        """Log alert attempt to database"""
        try:
            alert_log = AlertLog(
                reading_id=reading_id,
                alert_type=alert_type,
                alert_level=alert_level,
                recipient=recipient,
                message=message,
                success=success,
                error_message=error_message
            )
            
            db.session.add(alert_log)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error logging alert: {str(e)}")
            db.session.rollback()
    
    def check_and_send_alerts(self, reading: SensorReading, alert_level: str, messages: List[str]) -> Dict:
        """Check thresholds and send alerts if needed"""
        if alert_level == 'normal':
            return {"message": "No alerts needed"}
        
        # Check if we've already sent an alert for this reading
        if reading.alert_sent:
            return {"message": "Alert already sent for this reading"}
        
        # Check for alert fatigue - don't send too many alerts in short time
        if self._check_alert_fatigue(alert_level):
            logger.warning(f"Alert fatigue detected for {alert_level} alerts")
            return {"message": "Alert fatigue protection activated"}
        
        results = []
        
        # Default recipients (in real app, these would come from user settings)
        email_recipients = ['admin@example.com']  # Replace with actual email
        sms_recipients = ['+1234567890']  # Replace with actual phone number
        
        # Send email alerts
        for recipient in email_recipients:
            result = self.send_email_alert(reading, alert_level, messages, recipient)
            results.append({"type": "email", "recipient": recipient, "result": result})
        
        # Send SMS alerts for critical alerts
        if alert_level == 'critical':
            for recipient in sms_recipients:
                result = self.send_sms_alert(reading, alert_level, messages, recipient)
                results.append({"type": "sms", "recipient": recipient, "result": result})
        
        # Mark alert as sent
        reading.alert_sent = True
        db.session.commit()
        
        return {"alerts_sent": results}
    
    def _check_alert_fatigue(self, alert_level: str) -> bool:
        """Check if we're sending too many alerts of same level"""
        try:
            # Don't send more than 5 alerts of same level in 1 hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            recent_alerts = AlertLog.query.filter(
                AlertLog.alert_level == alert_level,
                AlertLog.sent_at >= one_hour_ago,
                AlertLog.success == True
            ).count()
            
            return recent_alerts >= 5
            
        except Exception as e:
            logger.error(f"Error checking alert fatigue: {str(e)}")
            return False
    
    def get_alert_history(self, limit: int = 50) -> List[Dict]:
        """Get recent alert history"""
        try:
            alerts = AlertLog.query.order_by(
                AlertLog.sent_at.desc()
            ).limit(limit).all()
            
            return [alert.to_dict() for alert in alerts]
            
        except Exception as e:
            logger.error(f"Error getting alert history: {str(e)}")
            return []
    
    def get_alert_statistics(self) -> Dict:
        """Get alert statistics"""
        try:
            # Get stats for last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            total_alerts = AlertLog.query.filter(
                AlertLog.sent_at >= yesterday
            ).count()
            
            successful_alerts = AlertLog.query.filter(
                AlertLog.sent_at >= yesterday,
                AlertLog.success == True
            ).count()
            
            email_alerts = AlertLog.query.filter(
                AlertLog.sent_at >= yesterday,
                AlertLog.alert_type == 'email'
            ).count()
            
            sms_alerts = AlertLog.query.filter(
                AlertLog.sent_at >= yesterday,
                AlertLog.alert_type == 'sms'
            ).count()
            
            critical_alerts = AlertLog.query.filter(
                AlertLog.sent_at >= yesterday,
                AlertLog.alert_level == 'critical'
            ).count()
            
            warning_alerts = AlertLog.query.filter(
                AlertLog.sent_at >= yesterday,
                AlertLog.alert_level == 'warning'
            ).count()
            
            return {
                'total_alerts': total_alerts,
                'successful_alerts': successful_alerts,
                'failed_alerts': total_alerts - successful_alerts,
                'email_alerts': email_alerts,
                'sms_alerts': sms_alerts,
                'critical_alerts': critical_alerts,
                'warning_alerts': warning_alerts,
                'success_rate': round(successful_alerts / total_alerts * 100, 1) if total_alerts > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting alert statistics: {str(e)}")
            return {
                'total_alerts': 0,
                'successful_alerts': 0,
                'failed_alerts': 0,
                'email_alerts': 0,
                'sms_alerts': 0,
                'critical_alerts': 0,
                'warning_alerts': 0,
                'success_rate': 0
            }