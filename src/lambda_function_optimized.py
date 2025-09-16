"""
La Marzocco Dashboard Lambda Function - Optimized Version

This function collects data from La Marzocco Cloud API and generates
a dashboard that's deployed to S3 for static hosting.

OPTIMIZATION: Only invalidates CloudFront when content actually changes.
"""

import json
import boto3
import logging
import os
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any
import asyncio
from jinja2 import Template

# Import the La Marzocco client
from pylamarzocco import LaMarzoccoCloudClient

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class LaMarzoccoDashboard:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.secrets_client = boto3.client('secretsmanager')
        self.cloudfront_client = boto3.client('cloudfront')
        
        # Environment variables
        self.bucket_name = os.environ['S3_BUCKET_NAME']
        self.secret_name = os.environ['LAMARZOCCO_SECRET_NAME']
        self.cloudfront_distribution_id = os.environ.get('CLOUDFRONT_DISTRIBUTION_ID')
        
        # Cache keys for content hashing
        self.html_cache_key = 'dashboard-html-hash'
        self.json_cache_key = 'dashboard-json-hash'
        
    async def get_credentials(self) -> Dict[str, str]:
        """Retrieve La Marzocco credentials from Secrets Manager"""
        try:
            response = self.secrets_client.get_secret_value(SecretId=self.secret_name)
            secret = json.loads(response['SecretString'])
            return {
                'username': secret['username'],
                'password': secret['password']
            }
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}")
            raise

    def get_content_hash(self, content: str) -> str:
        """Generate SHA256 hash of content for change detection"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def get_cached_hash(self, cache_key: str) -> str:
        """Get previously stored content hash from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=f'.cache/{cache_key}'
            )
            return response['Body'].read().decode('utf-8').strip()
        except self.s3_client.exceptions.NoSuchKey:
            logger.info(f"No cached hash found for {cache_key}")
            return ""
        except Exception as e:
            logger.warning(f"Error retrieving cached hash for {cache_key}: {e}")
            return ""

    def store_cached_hash(self, cache_key: str, content_hash: str):
        """Store content hash in S3 for future comparison"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=f'.cache/{cache_key}',
                Body=content_hash,
                ContentType='text/plain'
            )
            logger.info(f"Stored hash for {cache_key}: {content_hash[:8]}...")
        except Exception as e:
            logger.warning(f"Error storing cached hash for {cache_key}: {e}")

    def has_content_changed(self, content: str, cache_key: str) -> bool:
        """Check if content has changed since last update"""
        current_hash = self.get_content_hash(content)
        cached_hash = self.get_cached_hash(cache_key)
        
        if current_hash != cached_hash:
            logger.info(f"Content changed for {cache_key}: {cached_hash[:8]}... -> {current_hash[:8]}...")
            return True
        else:
            logger.info(f"Content unchanged for {cache_key}: {current_hash[:8]}...")
            return False

    async def collect_machine_data(self) -> Dict[str, Any]:
        """Collect data from La Marzocco Cloud API"""
        credentials = await self.get_credentials()
        
        try:
            # Initialize the client
            client = LaMarzoccoCloudClient(
                username=credentials['username'],
                password=credentials['password']
            )
            
            # Connect to the cloud
            await client.connect()
            
            # Get machine data
            machines = client.machines
            if not machines:
                raise Exception("No machines found in account")
            
            # Use the first machine
            machine = list(machines.values())[0]
            
            # Collect comprehensive machine data
            machine_data = {
                "machine_info": {
                    "name": getattr(machine, 'name', 'Unknown'),
                    "model": getattr(machine, 'model', 'Unknown'),
                    "serial_number": getattr(machine, 'serial_number', 'Unknown'),
                    "firmware_version": f"Gateway: {getattr(machine, 'gateway_version', 'Unknown')}, Machine: {getattr(machine, 'machine_version', 'Unknown')}",
                    "connected": getattr(machine, 'connected', False),
                    "connection_date": getattr(machine, 'connection_date', datetime.now(timezone.utc)).isoformat() if hasattr(machine, 'connection_date') else datetime.now(timezone.utc).isoformat(),
                    "image_url": getattr(machine, 'image_url', '')
                },
                "status": {
                    "power_on": getattr(machine, 'power', False),
                    "mode": getattr(machine, 'current_status', 'Unknown'),
                    "coffee_boiler_temp": getattr(machine, 'coffee_temp', 0),
                    "coffee_boiler_ready": getattr(machine, 'coffee_temp_ready', False),
                    "coffee_boiler_range": f"{getattr(machine, 'coffee_temp_min', 0)}-{getattr(machine, 'coffee_temp_max', 0)}°F",
                    "steam_boiler_status": "READY" if getattr(machine, 'steam_temp_ready', False) else "HEATING",
                    "steam_boiler_enabled": getattr(machine, 'steam_enabled', False),
                    "scale_connected": getattr(machine, 'scale_connected', False),
                    "scale_battery": getattr(machine, 'scale_battery', 0),
                    "scale_name": getattr(machine, 'scale_name', ''),
                    "scale_calibration_required": getattr(machine, 'scale_calibration_required', False)
                },
                "statistics": {
                    "total_shots": getattr(machine, 'total_shots', 0),
                    "total_flushes": getattr(machine, 'total_flushes', 0),
                    "last_cleaning": getattr(machine, 'last_cleaning', datetime.now(timezone.utc)).isoformat() if hasattr(machine, 'last_cleaning') else None
                },
                "brewing": {
                    "pre_brewing_mode": getattr(machine, 'pre_brewing_mode', 'Unknown'),
                    "pre_brewing_available": getattr(machine, 'pre_brewing_modes', []),
                    "dose_mode": getattr(machine, 'dose_mode', 'Unknown'),
                    "dose_1": getattr(machine, 'dose_1', 0),
                    "dose_2": getattr(machine, 'dose_2', 0),
                    "dose_range": f"{getattr(machine, 'dose_min', 0)}-{getattr(machine, 'dose_max', 0)}g"
                },
                "recent_shots": getattr(machine, 'recent_shots', [])[:5],  # Last 5 shots
                "settings": {
                    "wifi_ssid": getattr(machine, 'wifi_ssid', ''),
                    "wifi_signal": getattr(machine, 'wifi_signal', 0),
                    "plumbed_in": getattr(machine, 'plumbed_in', False),
                    "auto_update": getattr(machine, 'auto_update', False),
                    "smart_standby_enabled": getattr(machine, 'smart_standby_enabled', False),
                    "smart_standby_minutes": getattr(machine, 'smart_standby_minutes', 0)
                },
                "maintenance": {
                    "cleaning_status": getattr(machine, 'cleaning_status', 'Unknown'),
                    "last_cleaning_date": getattr(machine, 'last_cleaning_date', ''),
                    "firmware_update_required": getattr(machine, 'firmware_update_required', False),
                    "firmware_update_available": getattr(machine, 'firmware_update_available', False)
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "collection_method": "La Marzocco Cloud API",
                "client_version": "pylamarzocco"
            }
            
            await client.disconnect()
            logger.info("Successfully collected machine data")
            return machine_data
            
        except Exception as e:
            logger.error(f"Failed to collect machine data: {e}")
            raise

    def generate_dashboard_html(self, machine_data: Dict[str, Any]) -> str:
        """Generate HTML dashboard from machine data"""
        
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>La Marzocco Dashboard - {{ machine_data.machine_info.name }}</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>☕</text></svg>">
    <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' style='background:%23d4af37'><text y='.9em' font-size='90'>☕</text></svg>">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #8B4513 0%, #A0522D 50%, #CD853F 100%);
            color: #f5f5f5;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        
        .machine-image {
            max-width: 200px;
            max-height: 150px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
            margin: 10px 0;
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .status-card {
            background: rgba(0, 0, 0, 0.4);
            padding: 20px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .status-card h3 {
            color: #d4af37;
            margin-bottom: 15px;
            font-size: 1.2em;
            border-bottom: 2px solid #d4af37;
            padding-bottom: 5px;
        }
        
        .status-item {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .status-item:last-child {
            border-bottom: none;
        }
        
        .status-value {
            font-weight: bold;
            color: #d4af37;
        }
        
        .status-ready {
            color: #4CAF50;
        }
        
        .status-warning {
            color: #FF9800;
        }
        
        .status-error {
            color: #F44336;
        }
        
        .footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        
        .last-updated {
            font-size: 0.9em;
            color: #ccc;
            margin-bottom: 10px;
        }
        
        .auto-refresh {
            font-size: 0.8em;
            color: #999;
        }
        
        @media (max-width: 768px) {
            .status-grid {
                grid-template-columns: 1fr;
            }
            
            .container {
                padding: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>☕ La Marzocco Dashboard</h1>
            <h2>{{ machine_data.machine_info.name }}</h2>
            <p>{{ machine_data.machine_info.model }} - S/N: {{ machine_data.machine_info.serial_number }}</p>
            {% if machine_data.machine_info.image_url %}
            <img src="{{ machine_data.machine_info.image_url }}" alt="Machine Image" class="machine-image">
            {% endif %}
        </div>
        
        <div class="status-grid">
            <div class="status-card">
                <h3>🔋 Machine Status</h3>
                <div class="status-item">
                    <span>Power</span>
                    <span class="status-value {{ 'status-ready' if machine_data.status.power_on else 'status-error' }}">
                        {{ 'ON' if machine_data.status.power_on else 'OFF' }}
                    </span>
                </div>
                <div class="status-item">
                    <span>Mode</span>
                    <span class="status-value">{{ machine_data.status.mode }}</span>
                </div>
                <div class="status-item">
                    <span>Connected</span>
                    <span class="status-value {{ 'status-ready' if machine_data.machine_info.connected else 'status-error' }}">
                        {{ 'YES' if machine_data.machine_info.connected else 'NO' }}
                    </span>
                </div>
            </div>
            
            <div class="status-card">
                <h3>🌡️ Temperature</h3>
                <div class="status-item">
                    <span>Coffee Boiler</span>
                    <span class="status-value {{ 'status-ready' if machine_data.status.coffee_boiler_ready else 'status-warning' }}">
                        {{ machine_data.status.coffee_boiler_temp }}°F
                    </span>
                </div>
                <div class="status-item">
                    <span>Range</span>
                    <span class="status-value">{{ machine_data.status.coffee_boiler_range }}</span>
                </div>
                <div class="status-item">
                    <span>Steam Boiler</span>
                    <span class="status-value {{ 'status-ready' if machine_data.status.steam_boiler_status == 'READY' else 'status-warning' }}">
                        {{ machine_data.status.steam_boiler_status }}
                    </span>
                </div>
            </div>
            
            <div class="status-card">
                <h3>📊 Statistics</h3>
                <div class="status-item">
                    <span>Total Shots</span>
                    <span class="status-value">{{ machine_data.statistics.total_shots }}</span>
                </div>
                <div class="status-item">
                    <span>Total Flushes</span>
                    <span class="status-value">{{ machine_data.statistics.total_flushes }}</span>
                </div>
                {% if machine_data.statistics.last_cleaning %}
                <div class="status-item">
                    <span>Last Cleaning</span>
                    <span class="status-value">{{ machine_data.statistics.last_cleaning[:10] }}</span>
                </div>
                {% endif %}
            </div>
            
            <div class="status-card">
                <h3>⚖️ Scale</h3>
                <div class="status-item">
                    <span>Connected</span>
                    <span class="status-value {{ 'status-ready' if machine_data.status.scale_connected else 'status-error' }}">
                        {{ 'YES' if machine_data.status.scale_connected else 'NO' }}
                    </span>
                </div>
                {% if machine_data.status.scale_connected %}
                <div class="status-item">
                    <span>Battery</span>
                    <span class="status-value {{ 'status-ready' if machine_data.status.scale_battery > 20 else 'status-warning' }}">
                        {{ machine_data.status.scale_battery }}%
                    </span>
                </div>
                <div class="status-item">
                    <span>Name</span>
                    <span class="status-value">{{ machine_data.status.scale_name }}</span>
                </div>
                {% endif %}
            </div>
            
            <div class="status-card">
                <h3>☕ Brewing Settings</h3>
                <div class="status-item">
                    <span>Pre-brewing</span>
                    <span class="status-value">{{ machine_data.brewing.pre_brewing_mode }}</span>
                </div>
                <div class="status-item">
                    <span>Dose Mode</span>
                    <span class="status-value">{{ machine_data.brewing.dose_mode }}</span>
                </div>
                <div class="status-item">
                    <span>Dose 1</span>
                    <span class="status-value">{{ machine_data.brewing.dose_1 }}g</span>
                </div>
                <div class="status-item">
                    <span>Dose 2</span>
                    <span class="status-value">{{ machine_data.brewing.dose_2 }}g</span>
                </div>
            </div>
            
            <div class="status-card">
                <h3>🔧 Maintenance</h3>
                <div class="status-item">
                    <span>Cleaning Status</span>
                    <span class="status-value {{ 'status-ready' if machine_data.maintenance.cleaning_status == 'READY' else 'status-warning' }}">
                        {{ machine_data.maintenance.cleaning_status }}
                    </span>
                </div>
                <div class="status-item">
                    <span>Firmware Update</span>
                    <span class="status-value {{ 'status-warning' if machine_data.maintenance.firmware_update_required else 'status-ready' }}">
                        {{ 'REQUIRED' if machine_data.maintenance.firmware_update_required else 'UP TO DATE' }}
                    </span>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <div class="last-updated">
                Last Updated: <span id="lastUpdated">{{ machine_data.timestamp[:19].replace('T', ' ') }} UTC</span>
            </div>
            <div class="auto-refresh">
                Auto-refresh every 5 minutes | 
                <a href="/data.json" style="color: #d4af37;">JSON API</a> | 
                Powered by <a href="https://aws.amazon.com/lambda/" style="color: #d4af37;">AWS Lambda</a>
            </div>
        </div>
    </div>
    
    <script>
        // Auto-refresh every 5 minutes
        setTimeout(() => {
            window.location.reload();
        }, 300000);
        
        // Convert timestamp to local time
        document.addEventListener('DOMContentLoaded', function() {
            const lastUpdatedElement = document.getElementById('lastUpdated');
            const utcTime = '{{ machine_data.timestamp }}';
            const localTime = new Date(utcTime).toLocaleString();
            lastUpdatedElement.textContent = localTime;
        });
    </script>
</body>
</html>
        """
        
        template = Template(html_template)
        return template.render(machine_data=machine_data)

    async def upload_to_s3(self, content: str, key: str, content_type: str = 'text/html') -> bool:
        """Upload content to S3 and return True if content changed"""
        
        # Check if content has changed
        cache_key = f"{key}-hash"
        content_changed = self.has_content_changed(content, cache_key)
        
        if not content_changed:
            logger.info(f"Content unchanged for {key}, skipping S3 upload")
            return False
        
        try:
            # Upload the content
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                ContentType=content_type,
                CacheControl='max-age=300'  # 5 minutes cache
            )
            
            # Store the new hash
            self.store_cached_hash(cache_key, self.get_content_hash(content))
            
            logger.info(f"Successfully uploaded {key} to S3 (content changed)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload {key} to S3: {e}")
            raise

    async def invalidate_cloudfront(self, paths_to_invalidate: list):
        """Invalidate CloudFront cache for specific paths"""
        if not self.cloudfront_distribution_id:
            logger.info("No CloudFront distribution ID provided, skipping invalidation")
            return
            
        if not paths_to_invalidate:
            logger.info("No paths to invalidate")
            return
            
        try:
            response = self.cloudfront_client.create_invalidation(
                DistributionId=self.cloudfront_distribution_id,
                InvalidationBatch={
                    'Paths': {
                        'Quantity': len(paths_to_invalidate),
                        'Items': paths_to_invalidate
                    },
                    'CallerReference': f'lambda-{int(datetime.now().timestamp())}'
                }
            )
            
            logger.info(f"CloudFront invalidation created for {len(paths_to_invalidate)} paths: {response['Invalidation']['Id']}")
            
        except Exception as e:
            logger.warning(f"CloudFront invalidation failed: {e}")
            # Don't raise - this is not critical

    async def run(self):
        """Main execution function"""
        try:
            logger.info("Starting La Marzocco dashboard update")
            
            # Collect machine data
            machine_data = await self.collect_machine_data()
            
            # Generate content
            html_content = self.generate_dashboard_html(machine_data)
            json_content = json.dumps(machine_data, indent=2)
            
            # Upload to S3 and track what changed
            paths_to_invalidate = []
            
            # Upload HTML
            if await self.upload_to_s3(html_content, 'index.html', 'text/html'):
                paths_to_invalidate.append('/index.html')
                paths_to_invalidate.append('/')  # Also invalidate root
            
            # Upload JSON
            if await self.upload_to_s3(json_content, 'data.json', 'application/json'):
                paths_to_invalidate.append('/data.json')
            
            # Only invalidate CloudFront if content actually changed
            if paths_to_invalidate:
                await self.invalidate_cloudfront(paths_to_invalidate)
                logger.info(f"Dashboard updated successfully - {len(paths_to_invalidate)} paths invalidated")
            else:
                logger.info("Dashboard checked - no changes detected, no invalidation needed")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Dashboard updated successfully',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'paths_invalidated': paths_to_invalidate,
                    'invalidation_count': len(paths_to_invalidate)
                })
            }
            
        except Exception as e:
            logger.error(f"Dashboard update failed: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': str(e),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            }

async def lambda_handler(event, context):
    """AWS Lambda handler"""
    dashboard = LaMarzoccoDashboard()
    return await dashboard.run()

# For local testing
if __name__ == "__main__":
    import asyncio
    
    # Mock environment variables for local testing
    os.environ.setdefault('S3_BUCKET_NAME', 'test-bucket')
    os.environ.setdefault('LAMARZOCCO_SECRET_NAME', 'test-secret')
    os.environ.setdefault('CLOUDFRONT_DISTRIBUTION_ID', 'test-distribution')
    
    result = asyncio.run(lambda_handler({}, {}))
    print(json.dumps(result, indent=2))
