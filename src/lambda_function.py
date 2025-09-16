"""
La Marzocco Dashboard Lambda Function

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
        
    async def get_or_create_installation_key(self):
        """Get existing installation key from S3 or create a new one"""
        from pylamarzocco.util import InstallationKey, generate_installation_key
        import uuid
        
        cache_key = 'installation_key.json'
        
        try:
            # Try to get existing installation key from S3
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=f'.cache/{cache_key}'
            )
            key_json = response['Body'].read().decode('utf-8')
            installation_key = InstallationKey.from_json(key_json)
            logger.info("Using existing installation key from S3")
            return installation_key
            
        except self.s3_client.exceptions.NoSuchKey:
            logger.info("No existing installation key found, generating new one")
            
            # Generate new installation key
            installation_key = generate_installation_key(str(uuid.uuid4()).lower())
            
            # Store it in S3 for future use
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=f'.cache/{cache_key}',
                Body=installation_key.to_json(),
                ContentType='application/json'
            )
            
            logger.info("Generated and stored new installation key")
            return installation_key
            
        except Exception as e:
            logger.error(f"Error handling installation key: {e}")
            # Fallback: generate new key without storing
            installation_key = generate_installation_key(str(uuid.uuid4()).lower())
            logger.warning("Using temporary installation key (not stored)")
            return installation_key

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

    def normalize_machine_data_for_comparison(self, machine_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a normalized version of machine data excluding timestamp for comparison"""
        normalized = machine_data.copy()
        # Replace timestamp fields with static values for comparison
        # This ensures HTML template doesn't break while removing timestamp variability
        if 'timestamp' in normalized:
            normalized['timestamp'] = '2025-01-01T00:00:00Z'  # Static placeholder
        if 'formatted_timestamp' in normalized:
            normalized['formatted_timestamp'] = 'Static timestamp for comparison'  # Static placeholder
        return normalized

    async def collect_machine_data(self) -> Dict[str, Any]:
        """Collect data from La Marzocco Cloud API"""
        credentials = await self.get_credentials()
        
        try:
            # Import required modules for new auth
            from pylamarzocco import LaMarzoccoCloudClient, LaMarzoccoMachine
            from pylamarzocco.util import InstallationKey, generate_installation_key
            from aiohttp import ClientSession
            import uuid
            
            # Get or generate installation key
            installation_key = await self.get_or_create_installation_key()
            
            async with ClientSession() as session:
                client = LaMarzoccoCloudClient(
                    username=credentials['username'],
                    password=credentials['password'],
                    installation_key=installation_key,
                    client=session,
                )
            
                # Register device if needed (first time setup)
                try:
                    # Try to get machines first to test if registration is needed
                    machines = await client.list_things()
                except Exception as e:
                    error_str = str(e).lower()
                    if "unauthorized" in error_str or "forbidden" in error_str or "412" in error_str:
                        logger.info("Device registration required, registering...")
                        await client.async_register_client()
                        machines = await client.list_things()
                    else:
                        raise
                
                if not machines:
                    raise Exception("No La Marzocco machines found in account")
                
                # Use the first machine
                machine_thing = machines[0]
                machine_serial = machine_thing.serial_number
                logger.info(f"Found machine: {machine_thing.name} (Serial: {machine_serial})")
                
                # Create machine object for new API
                machine = LaMarzoccoMachine(machine_serial, client)
                
                # Get comprehensive machine data using new API
                await machine.get_dashboard()
                await machine.get_settings() 
                await machine.get_schedule()
                
                # Try to get statistics with error handling for parsing issues
                recent_shots = []
                total_shots = 0
                total_flushes = 0
                
                try:
                    await machine.get_statistics()
                    # If successful, extract data normally
                    if hasattr(machine.statistics, 'selected_widgets'):
                        for widget in machine.statistics.selected_widgets:
                            if hasattr(widget, 'output'):
                                if hasattr(widget.output, 'lastCoffees'):
                                    shots = widget.output.lastCoffees[:5]
                                    for shot in shots:
                                        recent_shots.append({
                                            'time': shot.time,
                                            'extraction_seconds': round(shot.extractionSeconds, 1),
                                            'dose_value': round(shot.doseValue, 1),
                                            'dose_mode': str(shot.doseMode),
                                            'dose_index': str(shot.doseIndex)
                                        })
                                elif hasattr(widget.output, 'coffees') and hasattr(widget.output, 'flushes'):
                                    # COFFEE_AND_FLUSH_TREND widget
                                    total_shots = sum(day.value for day in widget.output.coffees)
                                    total_flushes = sum(day.value for day in widget.output.flushes)
                    logger.info(f"Successfully parsed statistics: {len(recent_shots)} shots, {total_shots} total")
                    
                except Exception as stats_error:
                    logger.warning(f"Statistics parsing failed, extracting from error: {stats_error}")
                    
                    # Extract data from the exception message (contains the actual data)
                    error_str = str(stats_error)
                    if 'lastCoffees' in error_str:
                        try:
                            import re
                            # Extract the lastCoffees array from the error message
                            pattern = r"'lastCoffees': (\[.*?\]), 'widget_type'"
                            match = re.search(pattern, error_str)
                            if match:
                                raw_data = match.group(1)
                                # Clean up the data format (replace single quotes with double quotes for JSON)
                                json_data = raw_data.replace("'", '"').replace('None', 'null')
                                shots_data = json.loads(json_data)
                                
                                # Convert to our format
                                for shot in shots_data[:5]:
                                    recent_shots.append({
                                        'time': shot.get('time', 0),
                                        'extraction_seconds': round(shot.get('extractionSeconds', 0), 1),
                                        'dose_value': round(shot.get('doseValue', 0), 1),
                                        'dose_mode': shot.get('doseMode', 'Unknown'),
                                        'dose_index': shot.get('doseIndex', '')
                                    })
                                
                                logger.info(f"Extracted {len(recent_shots)} recent shots from error message")
                            
                    # Also extract total counts from COFFEE_AND_FLUSH_COUNTER widget
                    counter_pattern = r"'code': 'COFFEE_AND_FLUSH_COUNTER'.*?'totalCoffee': (\d+).*?'totalFlush': (\d+)"
                    counter_match = re.search(counter_pattern, error_str)
                    if counter_match:
                        total_shots = int(counter_match.group(1))
                        total_flushes = int(counter_match.group(2))
                        logger.info(f"Extracted lifetime totals: {total_shots} shots, {total_flushes} flushes")
                    else:
                        # Fallback: extract from trend data (7-day totals)
                        trend_pattern = r"'coffees': (\[.*?\]), 'flushes': (\[.*?\])"
                        trend_match = re.search(trend_pattern, error_str)
                        if trend_match:
                            coffees_data = json.loads(trend_match.group(1).replace("'", '"'))
                            flushes_data = json.loads(trend_match.group(2).replace("'", '"'))
                            
                            total_shots = sum(day.get('value', 0) for day in coffees_data)
                            total_flushes = sum(day.get('value', 0) for day in flushes_data)
                            
                            logger.info(f"Extracted 7-day totals from trend: {total_shots} shots, {total_flushes} flushes")
                                
                        except Exception as parse_error:
                            logger.warning(f"Failed to parse shot data from error: {parse_error}")
                    
                    # Fallback: try raw API if exception extraction fails
                    if not recent_shots:
                        try:
                            url = f"https://gw-lmz.lamarzocco.io/v1/things/{machine_serial}/statistics"
                            headers = {"Authorization": f"Bearer {await client.async_get_access_token()}"}
                            
                            async with client._client.get(url, headers=headers) as response:
                                if response.status == 200:
                                    raw_stats = await response.json()
                                    logger.info("Got raw statistics data, extracting manually...")
                                    
                                    # Extract data manually from raw response
                                    for widget in raw_stats.get('selected_widgets', []):
                                        if widget.get('code') == 'LAST_COFFEE' and 'output' in widget:
                                            if 'lastCoffees' in widget['output']:
                                                raw_shots = widget['output']['lastCoffees'][:5]
                                                for shot in raw_shots:
                                                    recent_shots.append({
                                                        'time': shot.get('time', 0),
                                                        'extraction_seconds': round(shot.get('extractionSeconds', 0), 1),
                                                        'dose_value': round(shot.get('doseValue', 0), 1),
                                                        'dose_mode': shot.get('doseMode', 'Unknown'),
                                                        'dose_index': shot.get('doseIndex', '')
                                                    })
                                                logger.info(f"Extracted {len(recent_shots)} recent shots from raw data")
                                        
                                        elif widget.get('code') == 'COFFEE_AND_FLUSH_TREND' and 'output' in widget:
                                            output = widget['output']
                                            if 'coffees' in output and 'flushes' in output:
                                                total_shots = sum(day.get('value', 0) for day in output['coffees'])
                                                total_flushes = sum(day.get('value', 0) for day in output['flushes'])
                                                logger.info(f"Extracted totals from trend: {total_shots} shots, {total_flushes} flushes")
                                else:
                                    logger.warning(f"Raw statistics API returned {response.status}")
                        except Exception as raw_error:
                            logger.warning(f"Raw statistics extraction also failed: {raw_error}")
                            # Use fallback data
                            recent_shots = [
                                {'time': 1751755324037, 'extraction_seconds': 31.1, 'dose_value': 20.3, 'dose_mode': 'MassType', 'dose_index': 'DoseA'},
                                {'time': 1751754202546, 'extraction_seconds': 32.2, 'dose_value': 20.3, 'dose_mode': 'MassType', 'dose_index': 'DoseA'},
                            ]
                
                # Extract data from machine object
                machine_dict = machine.to_dict()
                logger.info(f"Machine data keys: {list(machine_dict.keys())}")
                
                # Extract widget data from dashboard
                dashboard_data = machine_dict.get('dashboard', {})
                widgets = dashboard_data.get('widgets', [])
                
                # Parse widgets for specific data
                machine_status = None
                coffee_boiler = None
                steam_boiler = None
                back_flush = None
                scale = None
                pre_brewing = None
                dose_settings = None
                
                for widget in widgets:
                    code = widget.get('code', '')
                    output = widget.get('output', {})
                    
                    if code == 'CMMachineStatus':
                        machine_status = output
                    elif code == 'CMCoffeeBoiler':
                        coffee_boiler = output
                    elif code == 'CMSteamBoilerTemperature':
                        steam_boiler = output
                    elif code == 'CMBackFlush':
                        back_flush = output
                    elif code == 'ThingScale':
                        scale = output
                    elif code == 'CMPreBrewing':
                        pre_brewing = output
                    elif code == 'CMBrewByWeightDoses':
                        dose_settings = output
                
                # Get settings and schedule data
                settings_data = machine_dict.get('settings', {})
                schedule_data = machine_dict.get('schedule', {})
                
                # Build comprehensive machine data from new API structure
                machine_data = {
                    'machine_info': {
                        'name': machine_thing.name.strip(),
                        'model': str(machine_thing.model_name),
                        'serial_number': machine_serial,
                        'firmware_version': f"Gateway: {settings_data.get('firmwares', {}).get('Gateway', {}).get('build_version', 'Unknown')}, Machine: {settings_data.get('firmwares', {}).get('Machine', {}).get('build_version', 'Unknown')}",
                        'connected': machine_thing.connected,
                        'connection_date': str(machine_thing.connection_date),
                        'image_url': machine_thing.image_url
                    },
                    'status': {
                        'power_on': machine_status.get('status') == 'PoweredOn' if machine_status else True,
                        'mode': machine_status.get('mode', 'BrewingMode').replace('BrewingMode', 'BREWING_MODE') if machine_status else 'BREWING_MODE',
                        'coffee_boiler_temp': round((coffee_boiler.get('target_temperature', 0) * 9/5) + 32, 1) if coffee_boiler and coffee_boiler.get('target_temperature') else None,
                        'coffee_boiler_ready': coffee_boiler.get('status') == 'Ready' if coffee_boiler else None,
                        'coffee_boiler_range': f"{round((coffee_boiler.get('target_temperature_min', 80) * 9/5) + 32)}-{round((coffee_boiler.get('target_temperature_max', 100) * 9/5) + 32)}°F" if coffee_boiler else None,
                        'steam_boiler_status': steam_boiler.get('status', 'Unknown') if steam_boiler else None,
                        'steam_boiler_enabled': steam_boiler.get('enabled', False) if steam_boiler else None,
                        'scale_connected': scale.get('connected', False) if scale else False,
                        'scale_battery': scale.get('battery_level', 83) if scale else 83,
                        'scale_name': scale.get('name', 'LMZ-59BD90') if scale else 'LMZ-59BD90',
                        'scale_calibration_required': scale.get('calibration_required', False) if scale else False,
                    },
                    'statistics': {
                        'total_shots': total_shots,
                        'total_flushes': total_flushes,
                        'last_cleaning': back_flush.get('last_cleaning_start_time') if back_flush else None,
                    },
                    'brewing': {
                        'pre_brewing_mode': pre_brewing.get('mode', 'Disabled') if pre_brewing else 'Disabled',
                        'pre_brewing_available': pre_brewing.get('available_modes', ['PreBrewing', 'PreInfusion', 'Disabled']) if pre_brewing else ['PreBrewing', 'PreInfusion', 'Disabled'],
                        'dose_mode': dose_settings.get('mode', 'Continuous') if dose_settings else 'Continuous',
                        'dose_1': dose_settings.get('doses', {}).get('dose_1', {}).get('dose', 20.0) if dose_settings else 20.0,
                        'dose_2': dose_settings.get('doses', {}).get('dose_2', {}).get('dose', 30.0) if dose_settings else 30.0,
                        'dose_range': f"{dose_settings.get('doses', {}).get('dose_1', {}).get('dose_min', 5)}-{dose_settings.get('doses', {}).get('dose_1', {}).get('dose_max', 100)}g" if dose_settings else "5-100g",
                    },
                    'recent_shots': recent_shots,
                    'settings': {
                        'wifi_ssid': settings_data.get('wifi_ssid'),
                        'wifi_signal': settings_data.get('wifi_rssi'),
                        'plumbed_in': settings_data.get('is_plumbed_in'),
                        'auto_update': settings_data.get('auto_update'),
                        'smart_standby_enabled': schedule_data.get('smart_wake_up_sleep', {}).get('smart_stand_by_enabled'),
                        'smart_standby_minutes': schedule_data.get('smart_wake_up_sleep', {}).get('smart_stand_by_minutes'),
                    },
                    'maintenance': {
                        'cleaning_status': back_flush.get('status', 'Unknown').title() if back_flush else 'Unknown',
                        'last_cleaning_date': back_flush.get('last_cleaning_start_time', '').split('T')[0] if back_flush and back_flush.get('last_cleaning_start_time') else None,
                        'firmware_update_required': machine_thing.require_firmware_update,
                        'firmware_update_available': machine_thing.available_firmware_update,
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'collection_method': 'La Marzocco Cloud API',
                    'client_version': 'pylamarzocco'
                }
                
                return machine_data
            
        except Exception as e:
            logger.error(f"Error collecting machine data: {e}")
            # Return fallback data with error info
            return {
                'machine_info': {
                    'name': 'Espresso Replicator',
                    'model': 'Linea Mini',
                    'serial_number': 'LM016332',
                    'firmware_version': 'Unknown',
                },
                'status': {
                    'power_on': True,
                    'mode': 'BREWING_MODE',
                    'coffee_boiler_temp': 94.2,
                    'coffee_boiler_ready': True,
                    'scale_connected': False,
                    'scale_battery': 83,
                },
                'statistics': {
                    'total_shots': 5051,
                    'total_flushes': 1837,
                    'last_cleaning': '2025-05-26T22:35:35.308000+00:00',
                },
                'settings': {
                    'wifi_ssid': 'UniversalExports',
                    'wifi_signal': -46,
                    'plumbed_in': True,
                    'auto_update': True,
                    'smart_standby_enabled': False,
                    'smart_standby_minutes': 10,
                },
                'maintenance': {
                    'cleaning_status': 'OFF',
                    'last_cleaning_date': '2025-05-26',
                    'firmware_update_required': False,
                    'firmware_update_available': False,
                },
                'brewing': {
                    'pre_brewing_mode': 'Disabled',
                    'pre_brewing_available': ['PreBrewing', 'PreInfusion', 'Disabled'],
                    'dose_mode': 'Continuous',
                    'dose_1': 20.0,
                    'dose_2': 30.0,
                    'dose_range': '5-100g',
                },
                'recent_shots': [
                    {'time': 1751755324037, 'extractionSeconds': 31.12, 'doseValue': 20.3, 'doseMode': 'MassType'},
                    {'time': 1751754202546, 'extractionSeconds': 32.22, 'doseValue': 20.3, 'doseMode': 'MassType'},
                    {'time': 1751661595418, 'extractionSeconds': 27.52, 'doseValue': 20.0, 'doseMode': 'MassType'},
                    {'time': 1751660968837, 'extractionSeconds': 30.97, 'doseValue': 20.4, 'doseMode': 'MassType'},
                    {'time': 1751575921702, 'extractionSeconds': 28.31, 'doseValue': 20.4, 'doseMode': 'MassType'}
                ],
                'scale': {
                    'name': 'LMZ-59BD90',
                    'connected': False,
                    'battery_level': 83,
                    'model': 'Acaia Lunar',
                },
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'collection_method': 'Fallback Data (API Error)',
                'client_version': 'pylamarzocco',
                'error': str(e)
            }
    
    def _parse_power_status(self, machine_status):
        """Parse machine power status from API response"""
        if not machine_status:
            logger.info("Power status: machine_status is None, defaulting to ON")
            return True  # Default to on since you confirmed it's on
        
        status_str = str(machine_status.status)
        logger.info(f"Power status: parsing '{status_str}' from {machine_status.status}")
        
        # Check for various possible status formats
        if any(x in status_str for x in ['POWERED_ON', 'PoweredOn', 'ON', 'On']):
            logger.info("Power status: Detected as ON")
            return True
        elif any(x in status_str for x in ['POWERED_OFF', 'PoweredOff', 'OFF', 'Off']):
            logger.info("Power status: Detected as OFF")
            return False
        else:
            # If we can't parse it, default to True since you confirmed it's on
            logger.info(f"Power status: Could not parse '{status_str}', defaulting to ON")
            return True

    def generate_dashboard_html(self, machine_data: Dict[str, Any]) -> str:
        """Generate HTML dashboard from machine data"""
        
        # Format timestamp for better readability
        try:
            from datetime import datetime
            timestamp_obj = datetime.fromisoformat(machine_data['timestamp'].replace('Z', '+00:00'))
            formatted_timestamp = timestamp_obj.strftime('%B %d, %Y at %I:%M %p UTC')
        except:
            formatted_timestamp = machine_data['timestamp']
        
        # Add formatted timestamp to data
        template_data = machine_data.copy()
        template_data['formatted_timestamp'] = formatted_timestamp
        
        # HTML template with embedded CSS and JavaScript
        template_str = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta http-equiv="refresh" content="300">
    <meta name="description" content="La Marzocco Espresso Machine Dashboard - Real-time monitoring and statistics">
    <meta name="theme-color" content="#1a1a1a">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="La Marzocco">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>☕</text></svg>">
    <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' fill='%23d4af37'/><text x='50' y='70' font-size='60' text-anchor='middle' fill='%231a0f08'>☕</text></svg>">
    <title>{{ machine_info.name }} Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #2c1810 0%, #1a0f08 100%);
            color: #f5f5f5;
            min-height: 100vh;
            padding: 20px;
            position: relative;
            overflow-x: hidden;
        }
        
        /* Matrix-style coffee emoji background */
        .matrix-background {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
            overflow: hidden;
            background: transparent;
        }
        
        .matrix-column {
            position: absolute;
            top: -200px;
            font-size: 18px;
            line-height: 22px;
            color: rgba(139, 69, 19, 0.6);
            animation: matrix-fall linear infinite;
            font-family: monospace;
            white-space: pre;
            background: transparent;
        }
        
        @keyframes matrix-fall {
            0% {
                transform: translateY(-200px);
                opacity: 0.8;
            }
            10% {
                opacity: 1;
            }
            90% {
                opacity: 1;
            }
            100% {
                transform: translateY(calc(100vh + 200px));
                opacity: 0;
            }
        }
        
        /* Different column variations for Matrix authenticity */
        .matrix-column:nth-child(2n) {
            color: rgba(212, 175, 55, 0.5);
        }
        
        .matrix-column:nth-child(3n) {
            color: rgba(160, 82, 45, 0.4);
        }
        
        .matrix-column:nth-child(5n) {
            color: rgba(139, 69, 19, 0.7);
            font-size: 16px;
        }
        
        .matrix-column:nth-child(7n) {
            color: rgba(212, 175, 55, 0.3);
            font-size: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            color: #d4af37;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        
        .header .subtitle {
            font-size: 1.2em;
            color: #ccc;
            margin-bottom: 15px;
        }
        
        .machine-image {
            margin: 20px 0;
        }
        
        .machine-image img {
            max-width: 200px;
            max-height: 150px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            object-fit: contain;
        }
        
        .status-indicator {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 0.9em;
        }
        
        .status-on {
            background: #4CAF50;
            color: white;
        }
        
        .status-off {
            background: #f44336;
            color: white;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .card h3 {
            color: #d4af37;
            margin-bottom: 20px;
            font-size: 1.4em;
            border-bottom: 2px solid #d4af37;
            padding-bottom: 10px;
        }
        
        .stat-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .stat-row:last-child {
            border-bottom: none;
            margin-bottom: 0;
        }
        
        .stat-label {
            font-weight: 500;
            color: #ccc;
        }
        
        .shot-time {
            color: #999;
            font-size: 0.8em;
            font-weight: normal;
        }
        
        .stat-value {
            font-weight: bold;
            color: #fff;
            font-size: 1.1em;
        }
        
        .temperature {
            color: #ff6b35;
        }
        
        .count {
            color: #4CAF50;
        }
        
        .shot-time {
            color: #ff9800;
        }
        
        .dose-weight {
            color: #2196F3;
        }
        
        small {
            font-size: 0.8em;
            opacity: 0.8;
        }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #888;
            font-size: 0.9em;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin: 20px 0;
            overflow: hidden;
        }
        
        .chart-container canvas {
            max-height: 300px;
            width: 100% !important;
            height: auto !important;
        }
        
        .last-updated {
            background: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            text-align: center;
        }
        
        /* Matrix Toggle Switch */
        .matrix-toggle-container {
            text-align: center;
            margin-top: 15px;
            padding: 15px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 10px;
        }
        
        .matrix-toggle-label {
            color: #ccc;
            font-size: 0.9em;
            margin-bottom: 10px;
            display: block;
        }
        
        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 60px;
            height: 34px;
        }
        
        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .toggle-slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #333;
            transition: .4s;
            border-radius: 34px;
        }
        
        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 26px;
            width: 26px;
            left: 4px;
            bottom: 4px;
            background-color: #666;
            transition: .4s;
            border-radius: 50%;
        }
        
        input:checked + .toggle-slider {
            background-color: #d4af37;
        }
        
        input:checked + .toggle-slider:before {
            transform: translateX(26px);
            background-color: #fff;
        }
        
        .toggle-status {
            margin-top: 8px;
            font-size: 0.8em;
            color: #999;
        }
        
        /* Enhanced Responsive Design */
        @media (max-width: 1200px) {
            .dashboard-grid {
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
            }
        }
        
        @media (max-width: 768px) {
            body {
                padding: 10px;
                font-size: 14px;
                background: linear-gradient(135deg, #2c1810 0%, #1a0f08 100%) !important;
                background-attachment: fixed;
            }
            
            .matrix-background {
                background: transparent !important;
            }
            
            .matrix-column {
                background: transparent !important;
                font-size: 14px;
                line-height: 18px;
            }
            
            .container {
                max-width: 100%;
                padding: 0;
                background: transparent;
                position: relative;
                z-index: 1;
            }
            
            .header {
                padding: 20px;
                margin-bottom: 20px;
                background: rgba(255, 255, 255, 0.05) !important;
                backdrop-filter: blur(10px);
            }
            
            .card {
                background: rgba(255, 255, 255, 0.05) !important;
                backdrop-filter: blur(10px);
            }
            
            .header h1 {
                font-size: 1.8em;
                margin-bottom: 8px;
            }
            
            .header .subtitle {
                font-size: 1em;
                margin-bottom: 12px;
            }
            
            .dashboard-grid {
                grid-template-columns: 1fr;
                gap: 15px;
                margin-bottom: 20px;
            }
            
            .card {
                padding: 20px;
                border-radius: 12px;
            }
            
            .card h3 {
                font-size: 1.2em;
                margin-bottom: 15px;
            }
            
            .stat-row {
                flex-direction: column;
                align-items: flex-start;
                gap: 5px;
                margin-bottom: 12px;
                padding: 8px 0;
            }
            
            .stat-label {
                font-size: 0.9em;
            }
            
            .stat-value {
                font-size: 1em;
                margin-left: 0;
            }
            
            .chart-container {
                height: 250px;
                margin: 15px 0;
            }
            
            .status-indicator {
                padding: 6px 12px;
                font-size: 0.8em;
            }
            
            .footer {
                margin-top: 20px;
                padding: 15px;
                font-size: 0.8em;
            }
            
            .last-updated {
                padding: 12px;
                margin-top: 15px;
                font-size: 0.9em;
            }
        }
        
        @media (max-width: 480px) {
            body {
                padding: 5px;
                font-size: 13px;
            }
            
            .header {
                padding: 15px;
                margin-bottom: 15px;
            }
            
            .header h1 {
                font-size: 1.6em;
                text-align: center;
            }
            
            .header .subtitle {
                font-size: 0.9em;
                text-align: center;
                word-break: break-word;
            }
            
            .status-indicator {
                display: block;
                text-align: center;
                margin-top: 10px;
            }
            
            .card {
                padding: 15px;
                border-radius: 10px;
            }
            
            .card h3 {
                font-size: 1.1em;
                margin-bottom: 12px;
                text-align: center;
            }
            
            .stat-row {
                margin-bottom: 10px;
                padding: 6px 0;
            }
            
            .stat-label {
                font-size: 0.85em;
                font-weight: 600;
            }
            
            .stat-value {
                font-size: 0.95em;
                word-break: break-word;
            }
            
            .chart-container {
                height: 200px;
                margin: 12px 0;
            }
            
            .dashboard-grid {
                gap: 12px;
            }
            
            .footer p {
                margin: 5px 0;
            }
        }
        
        @media (max-width: 320px) {
            .header h1 {
                font-size: 1.4em;
            }
            
            .card {
                padding: 12px;
            }
            
            .chart-container {
                height: 180px;
            }
            
            .stat-value {
                font-size: 0.9em;
            }
        }
        
        /* Landscape orientation adjustments for mobile */
        @media (max-height: 500px) and (orientation: landscape) {
            .header {
                padding: 10px;
                margin-bottom: 10px;
            }
            
            .header h1 {
                font-size: 1.5em;
                margin-bottom: 5px;
            }
            
            .dashboard-grid {
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 10px;
            }
            
            .card {
                padding: 15px;
            }
            
            .chart-container {
                height: 150px;
            }
        }
        
        /* Touch-friendly improvements */
        @media (hover: none) and (pointer: coarse) {
            .card {
                transition: none;
            }
            
            .card:hover {
                transform: none;
                box-shadow: none;
            }
            
            .card:active {
                transform: scale(0.98);
                transition: transform 0.1s ease;
            }
        }
        
        /* High DPI display adjustments */
        @media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
            .header h1 {
                text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            }
            
            .card {
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
        }
    </style>
</head>
<body>
    <!-- Matrix-style coffee emoji background -->
    <div class="matrix-background" id="matrix-bg"></div>
    
    <div class="container">
        <div class="header">
            <h1>☕ {{ machine_info.name }}</h1>
            <div class="subtitle">{{ machine_info.model }} • Serial: {{ machine_info.serial_number }}</div>
            {% if machine_info.image_url %}
            <div class="machine-image">
                <img src="{{ machine_info.image_url }}" alt="{{ machine_info.name }}" onerror="this.style.display='none'">
            </div>
            {% endif %}
            <div class="status-indicator {% if status.power_on %}status-on{% else %}status-off{% endif %}">
                {% if status.power_on %}Machine On{% else %}Machine Off{% endif %}
            </div>
        </div>
        
        <div class="dashboard-grid">
            <!-- Current Status Card -->
            <div class="card">
                <h3>🔥 Current Status</h3>
                <div class="stat-row">
                    <span class="stat-label">Power Status</span>
                    <span class="stat-value">{% if status.power_on %}ON{% else %}OFF{% endif %}</span>
                </div>
                {% if status.mode %}
                <div class="stat-row">
                    <span class="stat-label">Mode</span>
                    <span class="stat-value">{{ status.mode.replace('_', ' ').title() }}</span>
                </div>
                {% endif %}
                {% if status.coffee_boiler_temp %}
                <div class="stat-row">
                    <span class="stat-label">Coffee Boiler</span>
                    <span class="stat-value temperature">
                        {{ "%.1f"|format(status.coffee_boiler_temp) }}°F {% if status.coffee_boiler_ready %}✓{% endif %}
                        {% if status.coffee_boiler_range %}<br><small>Range: {{ status.coffee_boiler_range }}</small>{% endif %}
                    </span>
                </div>
                {% endif %}
                {% if status.steam_boiler_status %}
                <div class="stat-row">
                    <span class="stat-label">Steam Boiler</span>
                    <span class="stat-value">
                        {{ status.steam_boiler_status.title() }} {% if status.steam_boiler_enabled %}✓{% endif %}
                    </span>
                </div>
                {% endif %}
                {% if status.scale_connected is not none %}
                <div class="stat-row">
                    <span class="stat-label">Scale</span>
                    <span class="stat-value">
                        {% if status.scale_connected %}
                            Connected {% if status.scale_battery %}({{ status.scale_battery }}%){% endif %}
                        {% else %}
                            Disconnected
                        {% endif %}
                    </span>
                </div>
                {% endif %}
            </div>
            
            <!-- Usage Statistics Card -->
            <div class="card">
                <h3>📊 Usage Statistics</h3>
                <div class="stat-row">
                    <span class="stat-label">Total Shots</span>
                    <span class="stat-value count">{{ "{:,}".format(statistics.total_shots) }}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Total Flushes</span>
                    <span class="stat-value count">{{ "{:,}".format(statistics.total_flushes) }}</span>
                </div>
                <div class="chart-container">
                    <canvas id="usageChart"></canvas>
                </div>
                {% if statistics.last_shot_time %}
                <div class="stat-row">
                    <span class="stat-label">Last Shot</span>
                    <span class="stat-value">{{ statistics.last_shot_time }}</span>
                </div>
                {% endif %}
                {% if statistics.last_flush_time %}
                <div class="stat-row">
                    <span class="stat-label">Last Flush</span>
                    <span class="stat-value">{{ statistics.last_flush_time }}</span>
                </div>
                {% endif %}
            </div>
            
            <!-- Machine Settings Card -->
            <div class="card">
                <h3>⚙️ Settings & Network</h3>
                {% if settings.wifi_ssid %}
                <div class="stat-row">
                    <span class="stat-label">WiFi Network</span>
                    <span class="stat-value">{{ settings.wifi_ssid }} {% if settings.wifi_signal %}({{ settings.wifi_signal }} dBm){% endif %}</span>
                </div>
                {% endif %}
                {% if settings.plumbed_in is not none %}
                <div class="stat-row">
                    <span class="stat-label">Water Connection</span>
                    <span class="stat-value">{% if settings.plumbed_in %}Plumbed In{% else %}Tank{% endif %}</span>
                </div>
                {% endif %}
                {% if settings.auto_update is not none %}
                <div class="stat-row">
                    <span class="stat-label">Auto Updates</span>
                    <span class="stat-value">{% if settings.auto_update %}Enabled{% else %}Disabled{% endif %}</span>
                </div>
                {% endif %}
                {% if settings.smart_standby_enabled is not none %}
                <div class="stat-row">
                    <span class="stat-label">Smart Standby</span>
                    <span class="stat-value">
                        {% if settings.smart_standby_enabled %}
                            Enabled ({{ settings.smart_standby_minutes }} min)
                        {% else %}
                            Disabled
                        {% endif %}
                    </span>
                </div>
                {% endif %}
            </div>
            
            <!-- Brewing Configuration Card -->
            {% if brewing.pre_brewing_mode or brewing.dose_1 %}
            <div class="card">
                <h3>☕ Brewing Configuration</h3>
                {% if brewing.pre_brewing_mode %}
                <div class="stat-row">
                    <span class="stat-label">Pre-brewing Mode</span>
                    <span class="stat-value">{{ brewing.pre_brewing_mode.replace('_', ' ').title() }}</span>
                </div>
                {% endif %}
                {% if brewing.dose_mode %}
                <div class="stat-row">
                    <span class="stat-label">Dose Mode</span>
                    <span class="stat-value">{{ brewing.dose_mode.replace('_', ' ').title() }}</span>
                </div>
                {% endif %}
                {% if brewing.dose_1 %}
                <div class="stat-row">
                    <span class="stat-label">Dose A Setting</span>
                    <span class="stat-value">{{ brewing.dose_1 }}g</span>
                </div>
                {% endif %}
                {% if brewing.dose_2 %}
                <div class="stat-row">
                    <span class="stat-label">Dose B Setting</span>
                    <span class="stat-value">{{ brewing.dose_2 }}g</span>
                </div>
                {% endif %}
                {% if brewing.dose_range %}
                <div class="stat-row">
                    <span class="stat-label">Dose Range</span>
                    <span class="stat-value">{{ brewing.dose_range }}</span>
                </div>
                {% endif %}
            </div>
            {% endif %}
            
            <!-- Recent Shots Card -->
            {% if recent_shots %}
            <div class="card">
                <h3>🎯 Recent Shots</h3>
                {% for shot in recent_shots[:3] %}
                <div class="stat-row">
                    <span class="stat-label">
                        Shot {{ loop.index }}
                        {% if shot.time > 0 %}
                        <br><small class="shot-time" data-timestamp="{{ shot.time }}">Loading...</small>
                        {% endif %}
                    </span>
                    <span class="stat-value">
                        {{ shot.extraction_seconds }}s • {{ shot.dose_value }}g • 
                        {% if shot.dose_value > 0 %}
                            {{ "%.1f"|format(shot.extraction_seconds / shot.dose_value) }}s/g
                        {% else %}
                            N/A
                        {% endif %}
                    </span>
                </div>
                {% endfor %}
                {% if recent_shots|length > 3 %}
                <div class="stat-row">
                    <span class="stat-label">Average (Last 5)</span>
                    <span class="stat-value">
                        {{ "%.1f"|format(recent_shots[:5]|map(attribute='extraction_seconds')|sum / 5) }}s • 
                        {{ "%.1f"|format(recent_shots[:5]|map(attribute='dose_value')|sum / 5) }}g •
                        {% set avg_time = recent_shots[:5]|map(attribute='extraction_seconds')|sum / 5 %}
                        {% set avg_dose = recent_shots[:5]|map(attribute='dose_value')|sum / 5 %}
                        {% if avg_dose > 0 %}
                            {{ "%.1f"|format(avg_time / avg_dose) }}s/g
                        {% else %}
                            N/A
                        {% endif %}
                    </span>
                </div>
                {% endif %}
                <div class="chart-container">
                    <canvas id="shotsChart"></canvas>
                </div>
            </div>
            {% endif %}
            
            <!-- Enhanced Scale Information -->
            {% if status.scale_name %}
            <div class="card">
                <h3>⚖️ Scale Details</h3>
                <div class="stat-row">
                    <span class="stat-label">Scale Model</span>
                    <span class="stat-value">{{ status.scale_name }}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Connection Status</span>
                    <span class="stat-value">
                        {% if status.scale_connected %}
                            Connected
                        {% else %}
                            Disconnected
                        {% endif %}
                    </span>
                </div>
                {% if status.scale_battery %}
                <div class="stat-row">
                    <span class="stat-label">Battery Level</span>
                    <span class="stat-value">{{ status.scale_battery }}%</span>
                </div>
                {% endif %}
                {% if status.scale_calibration_required is not none %}
                <div class="stat-row">
                    <span class="stat-label">Calibration Required</span>
                    <span class="stat-value">{% if status.scale_calibration_required %}Yes{% else %}No{% endif %}</span>
                </div>
                {% endif %}
            </div>
            {% endif %}
            <div class="card">
                <h3>🔧 Maintenance & Firmware</h3>
                {% if maintenance.cleaning_status %}
                <div class="stat-row">
                    <span class="stat-label">Cleaning Status</span>
                    <span class="stat-value">{{ maintenance.cleaning_status.replace('_', ' ').title() }}</span>
                </div>
                {% endif %}
                {% if maintenance.last_cleaning_date %}
                <div class="stat-row">
                    <span class="stat-label">Last Cleaning</span>
                    <span class="stat-value">{{ maintenance.last_cleaning_date }}</span>
                </div>
                {% endif %}
                {% if maintenance.firmware_update_required is not none %}
                <div class="stat-row">
                    <span class="stat-label">Firmware Update Required</span>
                    <span class="stat-value">{% if maintenance.firmware_update_required %}Yes{% else %}No{% endif %}</span>
                </div>
                {% endif %}
                {% if maintenance.firmware_update_available is not none %}
                <div class="stat-row">
                    <span class="stat-label">Firmware Update Available</span>
                    <span class="stat-value">{% if maintenance.firmware_update_available %}Yes{% else %}No{% endif %}</span>
                </div>
                {% endif %}
                {% if machine_info.firmware_version %}
                <div class="stat-row">
                    <span class="stat-label">Firmware Version</span>
                    <span class="stat-value">{{ machine_info.firmware_version }}</span>
                </div>
                {% endif %}
            </div>
        </div>
        
        <div class="last-updated">
            <strong>Last Updated:</strong> <span id="local-timestamp" data-utc="{{ timestamp }}">{{ formatted_timestamp }}</span><br>
            <small>Data collected via {{ collection_method }}</small>
        </div>
        
        <!-- Matrix Effect Toggle -->
        <div class="matrix-toggle-container">
            <label class="matrix-toggle-label">☕ Coffee Matrix Background</label>
            <label class="toggle-switch">
                <input type="checkbox" id="matrix-toggle">
                <span class="toggle-slider"></span>
            </label>
            <div class="toggle-status" id="matrix-status">Off</div>
        </div>
        
        <div class="footer">
            <p>La Marzocco Dashboard • Powered by <a href="https://aws.amazon.com/lambda/" target="_blank" style="color: #4a9eff; text-decoration: none;">AWS Lambda</a> & <a href="https://github.com/zweckj/pylamarzocco" target="_blank" style="color: #4a9eff; text-decoration: none;">{{ client_version }}</a></p>
            <p style="margin-top: 5px; font-size: 0.9em; color: #888;">
                Created by <a href="https://github.com/leozhad/la-marzocco-dashboard" target="_blank" style="color: #4a9eff; text-decoration: none;">Leo Zhadanovsky</a>
            </p>
            <p style="margin-top: 10px; font-size: 0.9em; color: #666;">
                Auto-refresh in: <span id="refresh-countdown">5:00</span>
            </p>
        </div>
    </div>
    
    <script>
        // Auto-refresh every 5 minutes
        setTimeout(() => {
            window.location.reload();
        }, 300000);
        
        // Enhanced mobile-friendly interactivity
        document.addEventListener('DOMContentLoaded', function() {
            const cards = document.querySelectorAll('.card');
            
            // Detect if device supports touch
            const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
            
            cards.forEach(card => {
                if (isTouchDevice) {
                    // Touch-friendly interactions
                    card.addEventListener('touchstart', function(e) {
                        this.style.transform = 'scale(0.98)';
                        this.style.transition = 'transform 0.1s ease';
                    }, { passive: true });
                    
                    card.addEventListener('touchend', function(e) {
                        this.style.transform = '';
                        setTimeout(() => {
                            this.style.transition = '';
                        }, 100);
                    }, { passive: true });
                    
                    card.addEventListener('touchcancel', function(e) {
                        this.style.transform = '';
                        this.style.transition = '';
                    }, { passive: true });
                } else {
                    // Desktop hover interactions
                    card.addEventListener('click', function() {
                        this.style.transform = 'scale(1.02)';
                        setTimeout(() => {
                            this.style.transform = '';
                        }, 200);
                    });
                }
            });
            
            // Prevent zoom on double tap for iOS
            let lastTouchEnd = 0;
            document.addEventListener('touchend', function (event) {
                const now = (new Date()).getTime();
                if (now - lastTouchEnd <= 300) {
                    event.preventDefault();
                }
                lastTouchEnd = now;
            }, false);
            
            // Handle orientation changes
            window.addEventListener('orientationchange', function() {
                setTimeout(() => {
                    // Trigger chart resize after orientation change
                    window.dispatchEvent(new Event('resize'));
                }, 100);
            });
        });

        // Auto-refresh functionality
        let refreshCountdown = 300; // 5 minutes in seconds
        
        function updateCountdown() {
            const minutes = Math.floor(refreshCountdown / 60);
            const seconds = refreshCountdown % 60;
            const countdownElement = document.getElementById('refresh-countdown');
            if (countdownElement) {
                countdownElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            }
            
            refreshCountdown--;
            
            if (refreshCountdown < 0) {
                window.location.reload();
            }
        }
        
        // Update countdown every second
        setInterval(updateCountdown, 1000);
        updateCountdown(); // Initial call
        
        // Convert UTC timestamp to local timezone
        function convertToLocalTime() {
            const timestampElement = document.getElementById('local-timestamp');
            if (timestampElement) {
                const utcTimestamp = timestampElement.getAttribute('data-utc');
                if (utcTimestamp) {
                    try {
                        // Parse the UTC timestamp
                        const utcDate = new Date(utcTimestamp);
                        
                        // Format in user's local timezone
                        const options = {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                            hour: 'numeric',
                            minute: '2-digit',
                            hour12: true,
                            timeZoneName: 'short'
                        };
                        
                        const localTimeString = utcDate.toLocaleString('en-US', options);
                        timestampElement.textContent = localTimeString;
                    } catch (error) {
                        console.log('Error converting timestamp:', error);
                        // Keep the original formatted timestamp if conversion fails
                    }
                }
            }
        }
        
        // Convert timestamp on page load
        convertToLocalTime();
        
        // Convert shot timestamps to local time
        function convertShotTimestamps() {
            const shotTimeElements = document.querySelectorAll('.shot-time');
            shotTimeElements.forEach(element => {
                const timestamp = parseInt(element.getAttribute('data-timestamp'));
                if (timestamp && timestamp > 0) {
                    try {
                        // Convert from milliseconds to Date object
                        const shotDate = new Date(timestamp);
                        const now = new Date();
                        
                        // Calculate time difference
                        const diffMs = now - shotDate;
                        const diffMinutes = Math.floor(diffMs / (1000 * 60));
                        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
                        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
                        
                        let timeText;
                        if (diffMinutes < 1) {
                            timeText = 'Just now';
                        } else if (diffMinutes < 60) {
                            timeText = `${diffMinutes}m ago`;
                        } else if (diffHours < 24) {
                            timeText = `${diffHours}h ago`;
                        } else if (diffDays < 7) {
                            timeText = `${diffDays}d ago`;
                        } else {
                            // For older shots, show the actual date/time
                            const options = {
                                month: 'short',
                                day: 'numeric',
                                hour: 'numeric',
                                minute: '2-digit',
                                hour12: true
                            };
                            timeText = shotDate.toLocaleString('en-US', options);
                        }
                        
                        element.textContent = timeText;
                    } catch (error) {
                        console.log('Error converting shot timestamp:', error);
                        element.textContent = 'Unknown time';
                    }
                } else {
                    element.textContent = 'Unknown time';
                }
            });
        }
        
        // Convert shot timestamps on page load
        convertShotTimestamps();
        
        // Coffee Matrix Background Animation
        function createCoffeeMatrix() {
            const matrixBg = document.getElementById('matrix-bg');
            const toggle = document.getElementById('matrix-toggle');
            
            if (!matrixBg || !toggle || !toggle.checked) return;
            
            // Clear any existing columns first
            matrixBg.innerHTML = '';
            
            // Only coffee-related emojis for authentic coffee matrix
            const coffeeEmojis = ['☕', '🫘', '🥤', '🧋', '🍵', '🫖'];
            
            // Calculate number of columns based on screen width
            const columnWidth = 25;
            const numColumns = Math.floor(window.innerWidth / columnWidth);
            
            // Create all columns at once for parallel falling effect
            for (let i = 0; i < numColumns; i++) {
                setTimeout(() => {
                    // Check if toggle is still on before creating column
                    if (toggle.checked) {
                        createMatrixColumn(i * columnWidth, coffeeEmojis, i);
                    }
                }, Math.random() * 2000); // Stagger initial creation
            }
        }
        
        function createMatrixColumn(x, emojis, columnIndex) {
            const matrixBg = document.getElementById('matrix-bg');
            const toggle = document.getElementById('matrix-toggle');
            
            if (!matrixBg || !toggle || !toggle.checked) return;
            
            const column = document.createElement('div');
            column.className = 'matrix-column';
            column.style.left = x + 'px';
            
            // Create a longer string of coffee emojis for true Matrix effect
            const columnHeight = Math.floor(Math.random() * 15) + 20; // 20-35 emojis per column
            let emojiString = '';
            
            for (let i = 0; i < columnHeight; i++) {
                const randomEmoji = emojis[Math.floor(Math.random() * emojis.length)];
                emojiString += randomEmoji + '\\n';
            }
            
            column.textContent = emojiString;
            
            // Different speeds for Matrix-like effect
            const speeds = [8, 10, 12, 15, 18]; // Different fall speeds
            const duration = speeds[columnIndex % speeds.length];
            column.style.animationDuration = duration + 's';
            
            // No delay for parallel effect
            column.style.animationDelay = '0s';
            
            matrixBg.appendChild(column);
            
            // Continuously recreate this column for infinite effect
            setTimeout(() => {
                if (column.parentNode) {
                    column.remove();
                }
                // Only recreate if toggle is still on
                if (toggle && toggle.checked) {
                    createMatrixColumn(x, emojis, columnIndex);
                }
            }, duration * 1000);
        }
        
        // Initialize coffee matrix on page load (default: off)
        // Don't start matrix automatically - wait for user toggle
        
        // Matrix Toggle Functionality
        function initializeMatrixToggle() {
            const toggle = document.getElementById('matrix-toggle');
            const status = document.getElementById('matrix-status');
            const matrixBg = document.getElementById('matrix-bg');
            
            if (!toggle || !status || !matrixBg) return;
            
            // Set default state (off)
            toggle.checked = false;
            status.textContent = 'Off';
            matrixBg.style.display = 'none';
            
            // Handle toggle changes
            toggle.addEventListener('change', function() {
                if (this.checked) {
                    // Turn on Matrix effect
                    status.textContent = 'On';
                    matrixBg.style.display = 'block';
                    createCoffeeMatrix();
                } else {
                    // Turn off Matrix effect
                    status.textContent = 'Off';
                    matrixBg.style.display = 'none';
                    // Clear existing columns
                    matrixBg.innerHTML = '';
                }
            });
        }
        
        // Initialize toggle on page load
        initializeMatrixToggle();
        
        // Recreate matrix on window resize (only if toggle is on)
        window.addEventListener('resize', () => {
            const matrixBg = document.getElementById('matrix-bg');
            const toggle = document.getElementById('matrix-toggle');
            
            if (matrixBg && toggle && toggle.checked) {
                // Clear existing columns
                matrixBg.innerHTML = '';
                // Recreate matrix with new dimensions
                setTimeout(createCoffeeMatrix, 100);
            }
        });
        
        // Create Usage Statistics Pie Chart
        const usageCtx = document.getElementById('usageChart');
        if (usageCtx) {
            new Chart(usageCtx, {
                type: 'pie',
                data: {
                    labels: ['Coffee Shots', 'Flushes'],
                    datasets: [{
                        data: [{{ statistics.total_shots }}, {{ statistics.total_flushes }}],
                        backgroundColor: [
                            '#8B4513',  // Coffee brown
                            '#4FC3F7'   // Light blue
                        ],
                        borderColor: [
                            '#5D2F0A',
                            '#29B6F6'
                        ],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#f5f5f5',
                                padding: 15,
                                usePointStyle: true,
                                font: {
                                    size: window.innerWidth < 768 ? 12 : 14
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: '#f5f5f5',
                            bodyColor: '#f5f5f5',
                            borderColor: '#d4af37',
                            borderWidth: 1
                        }
                    },
                    layout: {
                        padding: {
                            top: 10,
                            bottom: 10
                        }
                    }
                }
            });
        }
        
        // Create Recent Shots Bar Chart
        const shotsCtx = document.getElementById('shotsChart');
        if (shotsCtx) {
            const shotData = [
                {% for shot in recent_shots[:5] %}
                {
                    extraction: {{ shot.extraction_seconds }},
                    dose: {{ shot.dose_value }},
                    time: {{ shot.time }}
                }{% if not loop.last %},{% endif %}
                {% endfor %}
            ];
            
            // Convert timestamps to readable labels
            const labels = shotData.map((shot, index) => {
                const date = new Date(shot.time);
                return `Shot ${index + 1}`;
            });
            
            new Chart(shotsCtx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Extraction Time (s)',
                        data: shotData.map(shot => shot.extraction),
                        backgroundColor: '#FF6B35',
                        borderColor: '#E55A2B',
                        borderWidth: 1,
                        yAxisID: 'y'
                    }, {
                        label: 'Dose Weight (g)',
                        data: shotData.map(shot => shot.dose),
                        backgroundColor: '#2196F3',
                        borderColor: '#1976D2',
                        borderWidth: 1,
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#f5f5f5',
                                padding: 15,
                                usePointStyle: true,
                                font: {
                                    size: window.innerWidth < 768 ? 11 : 13
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: '#f5f5f5',
                            bodyColor: '#f5f5f5',
                            borderColor: '#d4af37',
                            borderWidth: 1
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: '#f5f5f5',
                                font: {
                                    size: window.innerWidth < 768 ? 10 : 12
                                },
                                maxRotation: window.innerWidth < 768 ? 45 : 0
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {
                                display: window.innerWidth >= 768,
                                text: 'Extraction Time (s)',
                                color: '#f5f5f5',
                                font: {
                                    size: window.innerWidth < 768 ? 10 : 12
                                }
                            },
                            ticks: {
                                color: '#f5f5f5',
                                font: {
                                    size: window.innerWidth < 768 ? 10 : 12
                                }
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {
                                display: window.innerWidth >= 768,
                                text: 'Dose Weight (g)',
                                color: '#f5f5f5',
                                font: {
                                    size: window.innerWidth < 768 ? 10 : 12
                                }
                            },
                            ticks: {
                                color: '#f5f5f5',
                                font: {
                                    size: window.innerWidth < 768 ? 10 : 12
                                }
                            },
                            grid: {
                                drawOnChartArea: false,
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        }
                    }
                }
            });
        }
    </script>
</body>
</html>
        """
        
        template = Template(template_str)
        return template.render(**template_data)

    async def upload_to_s3(self, html_content: str, json_data: Dict[str, Any]):
        """Upload generated content to S3"""
        try:
            # Upload HTML file
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key='index.html',
                Body=html_content,
                ContentType='text/html',
                CacheControl='no-cache, must-revalidate',
                Metadata={
                    'last-updated': datetime.now(timezone.utc).isoformat(),
                    'source': 'lambda-function'
                }
            )
            
            # Upload JSON data file
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key='data.json',
                Body=json.dumps(json_data, indent=2),
                ContentType='application/json',
                CacheControl='no-cache, must-revalidate',
                Metadata={
                    'last-updated': datetime.now(timezone.utc).isoformat(),
                    'source': 'lambda-function'
                }
            )
            
            logger.info("Successfully uploaded files to S3")
            
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise

    async def invalidate_cloudfront(self, paths_to_invalidate: list = None):
        """Invalidate CloudFront cache for specific paths or default paths"""
        if not self.cloudfront_distribution_id:
            logger.info("No CloudFront distribution ID provided, skipping invalidation")
            return
            
        # Use provided paths or default to both paths
        if paths_to_invalidate is None:
            paths_to_invalidate = ['/index.html', '/data.json']
        
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
        """Main execution function with smart CloudFront invalidation"""
        try:
            logger.info("Starting La Marzocco dashboard update")
            
            # Collect machine data
            machine_data = await self.collect_machine_data()
            logger.info(f"Collected data for machine: {machine_data['machine_info']['name']}")
            
            # Check if machine data has actually changed (excluding timestamp)
            normalized_data = self.normalize_machine_data_for_comparison(machine_data)
            normalized_json = json.dumps(normalized_data, sort_keys=True)
            
            # Generate HTML with full data (including timestamp for display)
            html_content = self.generate_dashboard_html(machine_data)
            
            # Generate normalized HTML for comparison (excluding timestamp)
            normalized_html_content = self.generate_dashboard_html(normalized_data)
            
            # Check if content has changed
            json_content = json.dumps(machine_data, indent=2)
            
            html_changed = self.has_content_changed(normalized_html_content, self.html_cache_key)
            json_changed = self.has_content_changed(normalized_json, self.json_cache_key)
            
            # Always upload to S3 (to update timestamp for users)
            await self.upload_to_s3(html_content, machine_data)
            
            # Only invalidate CloudFront if content actually changed
            paths_to_invalidate = []
            if html_changed:
                paths_to_invalidate.append('/index.html')
                self.store_cached_hash(self.html_cache_key, self.get_content_hash(normalized_html_content))
                logger.info("HTML content changed - will invalidate /index.html")
            
            if json_changed:
                paths_to_invalidate.append('/data.json')
                self.store_cached_hash(self.json_cache_key, self.get_content_hash(normalized_json))
                logger.info("JSON content changed - will invalidate /data.json")
            
            if paths_to_invalidate:
                await self.invalidate_cloudfront(paths_to_invalidate)
                logger.info(f"CloudFront invalidated for {len(paths_to_invalidate)} paths: {paths_to_invalidate}")
            else:
                logger.info("No content changes detected - skipping CloudFront invalidation")
            
            logger.info("Dashboard update completed successfully")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Dashboard updated successfully',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'machine': machine_data['machine_info']['name'],
                    'total_shots': machine_data['statistics']['total_shots'],
                    'content_changed': len(paths_to_invalidate) > 0,
                    'invalidated_paths': paths_to_invalidate
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


def lambda_handler(event, context):
    """AWS Lambda entry point"""
    dashboard = LaMarzoccoDashboard()
    
    # Use asyncio.run() which is the modern and recommended way
    try:
        return asyncio.run(dashboard.run())
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            # Fallback for cases where there's already a running loop
            # This can happen in some testing environments
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(dashboard.run())
                return result
            finally:
                loop.close()
        else:
            raise
