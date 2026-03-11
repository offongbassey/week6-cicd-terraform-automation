import json
import boto3
import os
from datetime import datetime

s3_client = boto3.client('s3')
cloudwatch = boto3.client('cloudwatch')

def publish_metric(metric_name, value, unit='Count'):
    """Publish a custom metric to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace='LambdaFileProcessor',
            MetricData=[{
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }]
        )
        print(f"✓ Published metric: {metric_name} = {value} {unit}")
    except Exception as e:
        print(f"✗ Error publishing metric: {str(e)}")

def format_bytes(bytes_value):
    """Convert bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"

def is_image(file_key):
    """Check if file is an image"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    return any(file_key.lower().endswith(ext) for ext in image_extensions)

def lambda_handler(event, context):
    try:
        # Publish invocation metric
        publish_metric('FunctionInvocations', 1, 'Count')
        
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        file_key = event['Records'][0]['s3']['object']['key']
        
        print(f"Processing file: {file_key} from bucket: {bucket_name}")
        
        response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
        file_size = response['ContentLength']
        
        # Publish file size metric
        publish_metric('FileSizeBytes', file_size, 'Bytes')
        
        # Categorize file size
        if file_size < 1024 * 100:
            publish_metric('SmallFiles', 1, 'Count')
        elif file_size < 1024 * 1024 * 10:
            publish_metric('MediumFiles', 1, 'Count')
        else:
            publish_metric('LargeFiles', 1, 'Count')
        
        # Build metadata
        metadata = {
            'fileName': os.path.basename(file_key),
            'bucketName': bucket_name,
            'fileSize': file_size,
            'fileSizeReadable': format_bytes(file_size),
            'contentType': response.get('ContentType', 'unknown'),
            'uploadTime': datetime.utcnow().isoformat(),
            'isImage': is_image(file_key)
        }
        
        # Categorize by type
        if is_image(file_key):
            publish_metric('ImageFiles', 1, 'Count')
        else:
            publish_metric('NonImageFiles', 1, 'Count')
        
        # Save metadata
        metadata_key = f"metadata/{os.path.splitext(os.path.basename(file_key))[0]}_metadata.json"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=metadata_key,
            Body=json.dumps(metadata, indent=2)
        )
        
        print(f"Metadata saved to: {metadata_key}")
        
        # Publish success metric
        publish_metric('SuccessfulProcessing', 1, 'Count')
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Success'})
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        publish_metric('ProcessingErrors', 1, 'Count')
        raise e