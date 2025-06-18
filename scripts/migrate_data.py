#!/usr/bin/env python3
"""
Ad-hoc migration script for MeterMate data.

This script performs the following migrations:
1. Updates field name from 'unit' to 'unit_of_measurement' in stored readings
2. Fixes incorrect 'kWh' units for water meters by changing them to 'L'

Usage:
    python scripts/migrate_data.py [--dry-run] [--config-path PATH]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add the custom_components path to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components"))

from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.helpers import storage
from homeassistant.util import dt as dt_util

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
DOMAIN = "metermate"
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_readings"

# Unit mapping for corrections
WATER_METER_KEYWORDS = ["water", "h2o", "aqua", "irrigation", "well"]
UNIT_CORRECTIONS = {
    "kWh": "L",  # Water meters should use liters, not kilowatt-hours
}


class MigrationError(Exception):
    """Custom exception for migration errors."""


class MeterMateMigrator:
    """Migrates MeterMate data to new format."""
    
    def __init__(self, config_path: str | None = None, *, dry_run: bool = False):
        """Initialize the migrator."""
        self.dry_run = dry_run
        self.config_path = config_path or "/workspaces/MeterMate/config"
        self.storage_path = Path(self.config_path) / ".storage"
        self.stats = {
            "total_entities": 0,
            "total_readings": 0,
            "updated_readings": 0,
            "unit_corrections": 0,
            "field_updates": 0,
            "errors": 0
        }
        
    def _is_water_meter(self, entity_id: str) -> bool:
        """Check if entity ID suggests it's a water meter."""
        entity_lower = entity_id.lower()
        return any(keyword in entity_lower for keyword in WATER_METER_KEYWORDS)
    
    def _should_correct_unit(self, entity_id: str, current_unit: str) -> str | None:
        """Determine if unit should be corrected and return new unit."""
        if self._is_water_meter(entity_id) and current_unit == "kWh":
            return "L"
        return None
    
    def _migrate_reading(self, entity_id: str, reading: dict[str, Any]) -> dict[str, Any]:
        """Migrate a single reading."""
        updated = False
        migrated_reading = reading.copy()
        
        # 1. Handle field name change: 'unit' -> 'unit_of_measurement'
        if "unit" in migrated_reading and ATTR_UNIT_OF_MEASUREMENT not in migrated_reading:
            migrated_reading[ATTR_UNIT_OF_MEASUREMENT] = migrated_reading["unit"]
            del migrated_reading["unit"]
            self.stats["field_updates"] += 1
            updated = True
            logger.debug("Updated field name for reading %s", reading.get("id", "unknown"))
        
        # 2. Handle unit corrections (e.g., kWh -> L for water meters)
        current_unit = migrated_reading.get(ATTR_UNIT_OF_MEASUREMENT, "kWh")
        new_unit = self._should_correct_unit(entity_id, current_unit)
        
        if new_unit:
            migrated_reading[ATTR_UNIT_OF_MEASUREMENT] = new_unit
            self.stats["unit_corrections"] += 1
            updated = True
            logger.info("Corrected unit for %s reading %s: %s -> %s", 
                       entity_id, reading.get("id", "unknown"), current_unit, new_unit)
        
        if updated:
            self.stats["updated_readings"] += 1
            # Update the updated_at timestamp
            migrated_reading["updated_at"] = dt_util.utcnow().isoformat()
        
        return migrated_reading
    
    def _load_storage_file(self) -> dict[str, Any] | None:
        """Load the MeterMate storage file."""
        storage_file = self.storage_path / f"core.store-{STORAGE_KEY}"
        
        if not storage_file.exists():
            logger.warning(f"Storage file not found: {storage_file}")
            return None
        
        try:
            with open(storage_file, 'r') as f:
                data = json.load(f)
            logger.info(f"Loaded storage file: {storage_file}")
            return data
        except (json.JSONDecodeError, IOError) as e:
            raise MigrationError(f"Failed to load storage file: {e}")
    
    def _save_storage_file(self, data: Dict[str, Any]) -> None:
        """Save the migrated data back to storage file."""
        storage_file = self.storage_path / f"core.store-{STORAGE_KEY}"
        
        if self.dry_run:
            logger.info(f"DRY RUN: Would save migrated data to {storage_file}")
            return
        
        # Create backup
        backup_file = storage_file.with_suffix(f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        if storage_file.exists():
            import shutil
            shutil.copy2(storage_file, backup_file)
            logger.info(f"Created backup: {backup_file}")
        
        try:
            # Ensure directory exists
            storage_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(storage_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved migrated data to {storage_file}")
        except IOError as e:
            raise MigrationError(f"Failed to save storage file: {e}")
    
    def migrate(self) -> None:
        """Perform the migration."""
        logger.info("Starting MeterMate data migration...")
        logger.info(f"Config path: {self.config_path}")
        logger.info(f"Storage path: {self.storage_path}")
        logger.info(f"Dry run: {self.dry_run}")
        
        # Load storage data
        storage_data = self._load_storage_file()
        if not storage_data:
            logger.info("No storage data found. Nothing to migrate.")
            return
        
        # Extract the actual data (Home Assistant storage format)
        readings_data = storage_data.get('data', {})
        if not readings_data:
            logger.info("No readings data found in storage. Nothing to migrate.")
            return
        
        logger.info(f"Found data for {len(readings_data)} entities")
        
        # Process each entity's readings
        migrated_data = {}
        
        for entity_id, readings in readings_data.items():
            self.stats['total_entities'] += 1
            logger.info(f"Processing entity: {entity_id}")
            
            if not isinstance(readings, list):
                logger.warning(f"Unexpected data format for entity {entity_id}, skipping")
                migrated_data[entity_id] = readings
                continue
            
            migrated_readings = []
            
            for reading in readings:
                self.stats['total_readings'] += 1
                
                try:
                    migrated_reading = self._migrate_reading(entity_id, reading)
                    migrated_readings.append(migrated_reading)
                except Exception as e:
                    logger.error(f"Failed to migrate reading for {entity_id}: {e}")
                    self.stats['errors'] += 1
                    # Keep original reading on error
                    migrated_readings.append(reading)
            
            migrated_data[entity_id] = migrated_readings
            logger.info(f"Processed {len(readings)} readings for {entity_id}")
        
        # Update storage data with migrated readings
        storage_data['data'] = migrated_data
        
        # Save migrated data
        self._save_storage_file(storage_data)
        
        # Print statistics
        self._print_statistics()
    
    def _print_statistics(self) -> None:
        """Print migration statistics."""
        logger.info("Migration completed!")
        logger.info("Statistics:")
        logger.info(f"  Total entities processed: {self.stats['total_entities']}")
        logger.info(f"  Total readings processed: {self.stats['total_readings']}")  
        logger.info(f"  Readings updated: {self.stats['updated_readings']}")
        logger.info(f"  Field name updates (unit -> unit_of_measurement): {self.stats['field_updates']}")
        logger.info(f"  Unit corrections (kWh -> L for water meters): {self.stats['unit_corrections']}")
        logger.info(f"  Errors: {self.stats['errors']}")
        
        if self.dry_run:
            logger.info("DRY RUN: No actual changes were made to files.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Migrate MeterMate data format")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making actual changes"
    )
    parser.add_argument(
        "--config-path",
        default="/workspaces/MeterMate/config",
        help="Path to Home Assistant config directory"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        migrator = MeterMateMigrator(
            config_path=args.config_path,
            dry_run=args.dry_run
        )
        migrator.migrate()
    except MigrationError as e:
        logger.error(f"Migration failed: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("Migration cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
