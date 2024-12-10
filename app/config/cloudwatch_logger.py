import logging
from pythonjsonlogger import jsonlogger
from datetime import datetime
from app.config.aws_config import cw_handler

def setup_cloudwatch_logger(service_name):
    # Create a custom JSON formatter
    class CustomJsonFormatter(jsonlogger.JsonFormatter):
        def add_fields(self, log_record, record, message_dict):
            super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
            log_record['timestamp'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            log_record['service'] = service_name
            
    # Create logger
    logger = logging.getLogger("service_logger")
    logger.setLevel(logging.INFO)
    
    # Set JSON formatter for CloudWatch
    formatter = CustomJsonFormatter('%(timestamp)s %(service)s %(levelname)s %(correlation_id)s %(message)s')
    cw_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(cw_handler)
    
    return logger 