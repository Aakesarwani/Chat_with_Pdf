import json
import time
import os
import tempfile
import uuid
from werkzeug.utils import secure_filename

# Global progress tracking
upload_progress = {
    'status': 'idle',
    'message': '',
    'progress': 0,
    'stage': ''
}

def handler(event, context):
    """Vercel serverless function handler"""
    
    # Get the path and method from the event
    path = event.get('path', '/')
    method = event.get('httpMethod', 'GET')
    
    # Simple routing
    if path == '/api/health':
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'status': 'healthy'})
        }
    elif path == '/api/test':
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'working',
                'message': 'Backend is deployed and working',
                'timestamp': str(time.time())
            })
        }
    elif path == '/api/progress':
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': upload_progress.get('status', 'idle'),
                'message': upload_progress.get('message', ''),
                'progress': upload_progress.get('progress', 0),
                'stage': upload_progress.get('stage', '')
            })
        }
    elif path == '/api/upload' and method == 'POST':
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Document processed successfully (simulated)',
                'collection_name': f"rag_pdf_{uuid.uuid4().hex[:8]}",
                'chunks_count': 10,
                'note': 'This is a simulated response.'
            })
        }
    elif path == '/api/chat' and method == 'POST':
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'answer': 'This is a simulated response. Full functionality requires all dependencies.',
                'sources': []
            })
        }
    else:
        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Endpoint not found'})
        }
