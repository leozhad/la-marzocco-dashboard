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
import math
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import mimetypes
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from http import HTTPMethod
from importlib.metadata import version
from typing import Dict, Any
from zoneinfo import ZoneInfo
import asyncio
from jinja2 import Template

# Import the La Marzocco client
from pylamarzocco import LaMarzoccoCloudClient
from pylamarzocco.const import CUSTOMER_APP_URL, WidgetType
from pylamarzocco.models import ThingStatistics

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


@lru_cache(maxsize=1)
def frontend_bundle():
    """Read frontend files once per process, in the checkout or Lambda package."""
    directory = Path(__file__).resolve().parent / "web"
    if not directory.is_dir():
        directory = Path(__file__).resolve().parent.parent / "web"
    assets = []
    hasher = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.name == "index.html":
            continue
        relative = path.relative_to(directory)
        if any(part.startswith(".") for part in relative.parts):
            continue
        name = relative.as_posix()
        content = path.read_bytes()
        content_type = {
            ".js": "text/javascript", ".css": "text/css", ".txt": "text/plain"
        }.get(path.suffix) or mimetypes.guess_type(name)[0] or "application/octet-stream"
        hasher.update(name.encode() + b"\0" + content + b"\0")
        assets.append((name, content, content_type))
    return (directory / "index.html").read_text(), hasher.hexdigest()[:16], tuple(assets)


class DashboardCloudClient(LaMarzoccoCloudClient):
    """Keep fields omitted by pylamarzocco's statistics models."""

    async def get_thing_statistics(self, serial_number: str) -> ThingStatistics:
        # Match the pinned client's endpoint and authenticated request handling.
        # Its typed models omit shot doseValue/targetTemperature and daily flushes.
        payload = await self._rest_api_call(
            url=f"{CUSTOMER_APP_URL}/things/{serial_number}/stats",
            method=HTTPMethod.GET,
        )
        self.statistics_payload = deepcopy(payload)
        return ThingStatistics.from_dict(payload)


def extract_statistics(statistics: ThingStatistics, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Combine typed lifetime counters with raw shot weights and daily activity."""
    counter = statistics.widgets.get(WidgetType.COFFEE_AND_FLUSH_COUNTER)
    if counter is None:
        raise ValueError("Lifetime coffee and flush counters are missing")

    raw_widgets = {
        widget["code"]: widget.get("output", {})
        for widget in payload.get("selectedWidgets", [])
    }
    raw_shots = {
        shot["time"]: shot
        for shot in raw_widgets.get("LAST_COFFEE", {}).get("lastCoffees", [])
    }
    recent_shots = []
    last_coffee = statistics.widgets.get(WidgetType.LAST_COFFEE)
    if last_coffee:
        for shot in sorted(last_coffee.last_coffees, key=lambda item: item.time, reverse=True):
            timestamp = round(shot.time.timestamp() * 1000)
            raw_shot = raw_shots.get(timestamp, {})
            dose = raw_shot.get("doseValue")
            if (
                isinstance(dose, bool)
                or not isinstance(dose, (int, float))
                or not math.isfinite(dose)
            ):
                continue
            target = raw_shot.get("targetTemperature")
            recent_shots.append({
                "time": timestamp,
                "extraction_seconds": round(shot.extraction_seconds, 1),
                "dose_value": round(dose, 1),
                "dose_mode": str(shot.dose_mode),
                "dose_index": str(shot.dose_index),
                "target_temperature_f": (
                    round(target * 9 / 5 + 32, 1)
                    if isinstance(target, (int, float)) and math.isfinite(target)
                    else None
                ),
            })
            if len(recent_shots) == 5:
                break

    usage_trend = None
    trend = raw_widgets.get("COFFEE_AND_FLUSH_TREND")
    if trend:
        zone = ZoneInfo(trend["timezone"])
        daily = {}
        for source, field in [("coffees", "shots"), ("flushes", "flushes")]:
            for event in trend.get(source, []):
                local_date = datetime.fromtimestamp(
                    event["timestamp"] / 1000, tz=zone
                ).date()
                date = local_date.isoformat()
                day = daily.setdefault(date, {
                    "date": date,
                    "label": local_date.strftime("%a %b %d"),
                    "shots": 0,
                    "flushes": 0,
                })
                day[field] += event["value"]
        days = sorted(daily.values(), key=lambda day: day["date"])
        if days:
            usage_trend = {
                "days": trend["days"],
                "timezone": trend["timezone"],
                "daily": days,
                "total_shots": sum(day["shots"] for day in days),
                "total_flushes": sum(day["flushes"] for day in days),
            }

    return {
        "total_shots": counter.total_coffee,
        "total_flushes": counter.total_flush,
        "recent_shots": recent_shots,
        "usage_trend": usage_trend,
    }


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
            from pylamarzocco import LaMarzoccoMachine
            from aiohttp import ClientSession
            
            # Get or generate installation key
            installation_key = await self.get_or_create_installation_key()
            
            async with ClientSession() as session:
                client = DashboardCloudClient(
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
                
                await machine.get_statistics()
                stats = extract_statistics(machine.statistics, client.statistics_payload)
                logger.info(
                    "Collected statistics: %s lifetime shots, %s lifetime flushes, %s recent shots",
                    stats["total_shots"], stats["total_flushes"], len(stats["recent_shots"]),
                )

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
                standby = schedule_data.get('smart_stand_by') or {}
                legacy_standby = schedule_data.get('smart_wake_up_sleep') or {}
                
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
                        'total_shots': stats['total_shots'],
                        'total_flushes': stats['total_flushes'],
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
                    'recent_shots': stats['recent_shots'],
                    'usage_trend': stats['usage_trend'],
                    'settings': {
                        'wifi_ssid': settings_data.get('wifi_ssid'),
                        'wifi_signal': settings_data.get('wifi_rssi'),
                        'plumbed_in': settings_data.get('is_plumbed_in'),
                        'auto_update': settings_data.get('auto_update'),
                        'smart_standby_enabled': standby.get('enabled', legacy_standby.get('smart_stand_by_enabled')),
                        'smart_standby_minutes': standby.get('minutes', legacy_standby.get('smart_stand_by_minutes')),
                    },
                    'maintenance': {
                        'cleaning_status': back_flush.get('status', 'Unknown').title() if back_flush else 'Unknown',
                        'last_cleaning_date': back_flush.get('last_cleaning_start_time', '').split('T')[0] if back_flush and back_flush.get('last_cleaning_start_time') else None,
                        'firmware_update_required': machine_thing.require_firmware_update,
                        'firmware_update_available': machine_thing.available_firmware_update,
                        'firmware_notes': [
                            {
                                'name': name,
                                'version': firmware.get('build_version', ''),
                                'notes': firmware['change_log'],
                            }
                            for name, firmware in settings_data.get('firmwares', {}).items()
                            if firmware.get('change_log')
                        ],
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'collection_method': 'La Marzocco Cloud API',
                    'client_version': version('pylamarzocco')
                }
                
                return machine_data
            
        except Exception as e:
            logger.error(f"Error collecting machine data: {e}")
            # Let run() report the failure without overwriting the last good S3 data.
            raise

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
        """Render the dashboard with an initial data snapshot and versioned assets."""
        template, digest, _ = frontend_bundle()
        return Template(template, autoescape=True).render(
            dashboard_data=machine_data,
            asset_prefix=f"/assets/{digest}",
        )

    async def publish_frontend_assets(self):
        """Publish an immutable frontend before HTML can reference its modules."""
        _, digest, assets = frontend_bundle()
        marker = f".cache/frontend-assets/{digest}"
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=marker)
            return
        except ClientError as error:
            if error.response["Error"]["Code"] not in {"404", "NoSuchKey", "NotFound"}:
                raise
        for name, content, content_type in assets:
            self.s3_client.put_object(
                Bucket=self.bucket_name, Key=f"assets/{digest}/{name}", Body=content,
                ContentType=content_type, CacheControl="public, max-age=31536000, immutable",
            )
        self.s3_client.put_object(
            Bucket=self.bucket_name, Key=marker, Body=digest.encode(), ContentType="text/plain"
        )
        logger.info("Published frontend assets: %s", digest)

    async def upload_to_s3(self, html_content: str, json_data: Dict[str, Any]):
        """Upload generated content to S3"""
        try:
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
            
            await self.publish_frontend_assets()
            # Refresh data and HTML after the complete asset bundle is available.
            await self.upload_to_s3(html_content, machine_data)
            
            # Only invalidate CloudFront if content actually changed
            paths_to_invalidate = []
            if html_changed:
                paths_to_invalidate.extend(['/', '/index.html'])
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
