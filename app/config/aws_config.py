import boto3
import watchtower
import configparser

# Read config
config = configparser.ConfigParser()
config.read('config.ini')

# Initialize boto3 session with credentials
boto_sess = boto3.Session(
    aws_access_key_id=config['aws']['aws_access_key_id'],
    aws_secret_access_key=config['aws']['aws_secret_access_key'],
    region_name=config['aws']['region']
)

# Initialize CloudWatch handler
cw_handler = watchtower.CloudWatchLogHandler(
    log_group="/fastapi/order-service",
    stream_name="api-logs",
    boto3_client=boto_sess.client('logs')
)

# Add after the existing CloudWatch configuration
sqs_client =boto_sess.client('sqs')
SQS_QUEUE_URL = config['aws']['sqs_queue_url']