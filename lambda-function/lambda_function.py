import json
import boto3
from datetime import datetime
import os

# Initialize AWS S3 client
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    Main Lambda function handler.
    Triggered when a file is uploaded to S3.
    """
    
    try:
        # Extract bucket and file information from the event
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        file_key = event['Records'][0]['s3']['object']['key']
        file_size = event['Records'][0]['s3']['object']['size']
        
        print(f"Processing file: {file_key} from bucket: {bucket_name}")
        
        # Get file metadata from S3
        response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
        
        # Extract metadata
        metadata = {
            'fileName': file_key,
            'bucketName': bucket_name,
            'fileSize': file_size,
            'fileSizeReadable': format_bytes(file_size),
            'contentType': response.get('ContentType', 'unknown'),
            'lastModified': response['LastModified'].isoformat(),
            'etag': response['ETag'],
            'uploadTime': datetime.utcnow().isoformat(),
            'processedBy': 'AWS Lambda'
        }
        
        # If it's an image, try to get dimensions
        if is_image(file_key):
            try:
                # Download image temporarily to get dimensions
                download_path = f'/tmp/{os.path.basename(file_key)}'
                s3_client.download_file(bucket_name, file_key, download_path)
                
                # Get image dimensions using PIL
                from PIL import Image
                with Image.open(download_path) as img:
                    metadata['imageWidth'] = img.width
                    metadata['imageHeight'] = img.height
                    metadata['imageFormat'] = img.format
                    metadata['imageMode'] = img.mode
                
                # Clean up temp file
                os.remove(download_path)
                
            except Exception as img_error:
                print(f"Could not extract image dimensions: {img_error}")
                metadata['imageError'] = str(img_error)
        
        # Save metadata as JSON file
        metadata_key = f"metadata/{os.path.splitext(file_key)[0]}_metadata.json"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=metadata_key,
            Body=json.dumps(metadata, indent=2),
            ContentType='application/json'
        )
        
        print(f"Metadata saved to: {metadata_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'File processed successfully',
                'metadata': metadata
            })
        }
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error processing file',
                'error': str(e)
            })
        }

def format_bytes(size):
    """Convert bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def is_image(filename):
    """Check if file is an image based on extension"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    return any(filename.lower().endswith(ext) for ext in image_extensions)