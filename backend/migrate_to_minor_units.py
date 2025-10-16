#!/usr/bin/env python3
"""
Migration Script: Convert decimal monetary values to minor units

Usage:
    python migrate_to_minor_units.py --dry-run  # Preview changes without writing
    python migrate_to_minor_units.py            # Execute migration

Requirements:
    - MIGRATION_MONETARY_V1=true in .env to enable
    - Idempotent: safe to run multiple times
    - Generates backup and detailed report
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import asyncio
import json

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configuration
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ.get('DB_NAME', 'ristobrain_db')
MIGRATION_ENABLED = os.environ.get('MIGRATION_MONETARY_V1', 'false').lower() == 'true'

# Collections and fields to migrate
MIGRATION_MAP = {
    'ingredients': ['packCost', 'unitCost'],
    'recipes': ['price'],
    'sales': [],  # Will handle lines array specially
    'pl': ['revenue', 'cogs', 'grossMargin']
}

class MigrationReport:
    def __init__(self):
        self.collections = {}
        self.errors = []
        self.start_time = datetime.now()
    
    def add_collection(self, collection, updated, skipped, errors):
        self.collections[collection] = {
            'updated': updated,
            'skipped': skipped,
            'errors': errors
        }
    
    def add_error(self, error):
        self.errors.append(error)
    
    def generate(self):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        report = {
            'migration': 'MIGRATION_MONETARY_V1',
            'timestamp': self.start_time.isoformat(),
            'duration_seconds': duration,
            'collections': self.collections,
            'global_errors': self.errors,
            'summary': {
                'total_updated': sum(c['updated'] for c in self.collections.values()),
                'total_skipped': sum(c['skipped'] for c in self.collections.values()),
                'total_errors': sum(len(c['errors']) for c in self.collections.values()) + len(self.errors)
            }
        }
        
        return report

async def backup_collection(db, collection_name, dry_run=False):
    """Create backup of collection before migration"""
    if dry_run:
        print(f"  [DRY-RUN] Would backup {collection_name}")
        return None
    
    backup_name = f"{collection_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    docs = await db[collection_name].find({}).to_list(None)
    
    if docs:
        await db[backup_name].insert_many(docs)
        print(f"  ✓ Backed up {len(docs)} documents to {backup_name}")
    
    return backup_name

def to_minor_units(value, currency_code="EUR"):
    """Convert decimal to minor units"""
    if isinstance(value, int):
        return value  # Already in minor units
    
    minor_unit = 100  # EUR and USD both use 2 decimals
    return int(round(float(value) * minor_unit))

async def migrate_ingredients(db, dry_run=False):
    """Migrate ingredients collection"""
    print("\n[Ingredients Migration]")
    updated = 0
    skipped = 0
    errors = []
    
    await backup_collection(db, 'ingredients', dry_run)
    
    cursor = db.ingredients.find({})
    async for doc in cursor:
        try:
            # Check if already migrated (has currency field)
            if 'currencyCode' in doc:
                skipped += 1
                continue
            
            updates = {
                'packCost': to_minor_units(doc.get('packCost', 0)),
                'unitCost': to_minor_units(doc.get('unitCost', 0)),
                'currencyCode': 'EUR'  # Migration marker
            }
            
            if dry_run:
                print(f"  [DRY-RUN] Would update {doc['name']}: packCost={doc.get('packCost')} -> {updates['packCost']}")
            else:
                await db.ingredients.update_one(
                    {'_id': doc['_id']},
                    {'$set': updates}
                )
                updated += 1
        
        except Exception as e:
            errors.append({'id': str(doc.get('_id')), 'error': str(e)})
    
    print(f"  Updated: {updated}, Skipped: {skipped}, Errors: {len(errors)}")
    return updated, skipped, errors

async def migrate_recipes(db, dry_run=False):
    """Migrate recipes collection"""
    print("\n[Recipes Migration]")
    updated = 0
    skipped = 0
    errors = []
    
    await backup_collection(db, 'recipes', dry_run)
    
    cursor = db.recipes.find({})
    async for doc in cursor:
        try:
            if 'currencyCode' in doc:
                skipped += 1
                continue
            
            updates = {
                'price': to_minor_units(doc.get('price', 0)),
                'currencyCode': 'EUR'
            }
            
            if dry_run:
                print(f"  [DRY-RUN] Would update {doc['name']}: price={doc.get('price')} -> {updates['price']}")
            else:
                await db.recipes.update_one(
                    {'_id': doc['_id']},
                    {'$set': updates}
                )
                updated += 1
        
        except Exception as e:
            errors.append({'id': str(doc.get('_id')), 'error': str(e)})
    
    print(f"  Updated: {updated}, Skipped: {skipped}, Errors: {len(errors)}")
    return updated, skipped, errors

async def migrate_pl(db, dry_run=False):
    """Migrate P&L collection"""
    print("\n[P&L Migration]")
    updated = 0
    skipped = 0
    errors = []
    
    await backup_collection(db, 'pl', dry_run)
    
    cursor = db.pl.find({})
    async for doc in cursor:
        try:
            if 'currencyCode' in doc:
                skipped += 1
                continue
            
            updates = {
                'revenue': to_minor_units(doc.get('revenue', 0)),
                'cogs': to_minor_units(doc.get('cogs', 0)),
                'grossMargin': to_minor_units(doc.get('grossMargin', 0)),
                'currencyCode': 'EUR'
            }
            
            if dry_run:
                print(f"  [DRY-RUN] Would update {doc['month']}: revenue={doc.get('revenue')} -> {updates['revenue']}")
            else:
                await db.pl.update_one(
                    {'_id': doc['_id']},
                    {'$set': updates}
                )
                updated += 1
        
        except Exception as e:
            errors.append({'id': str(doc.get('_id')), 'error': str(e)})
    
    print(f"  Updated: {updated}, Skipped: {skipped}, Errors: {len(errors)}")
    return updated, skipped, errors

async def run_migration(dry_run=False):
    """Execute migration"""
    if not MIGRATION_ENABLED and not dry_run:
        print("❌ Migration not enabled. Set MIGRATION_MONETARY_V1=true in .env")
        return
    
    print("="*60)
    print("MIGRATION: Decimal to Minor Units (MONETARY_V1)")
    print("="*60)
    print(f"Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    print(f"Database: {DB_NAME}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*60)
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    report = MigrationReport()
    
    try:
        # Migrate each collection
        updated, skipped, errors = await migrate_ingredients(db, dry_run)
        report.add_collection('ingredients', updated, skipped, errors)
        
        updated, skipped, errors = await migrate_recipes(db, dry_run)
        report.add_collection('recipes', updated, skipped, errors)
        
        updated, skipped, errors = await migrate_pl(db, dry_run)
        report.add_collection('pl', updated, skipped, errors)
        
    except Exception as e:
        report.add_error(str(e))
        print(f"\n❌ Migration failed: {str(e)}")
    
    finally:
        client.close()
    
    # Generate and save report
    report_data = report.generate()
    report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    print(f"Total Updated: {report_data['summary']['total_updated']}")
    print(f"Total Skipped: {report_data['summary']['total_skipped']}")
    print(f"Total Errors: {report_data['summary']['total_errors']}")
    print(f"Duration: {report_data['duration_seconds']:.2f}s")
    print(f"Report saved to: {report_file}")
    print("="*60)
    
    if dry_run:
        print("\n✓ DRY-RUN completed. No data was modified.")
    else:
        print("\n✓ Migration completed successfully!")

def main():
    parser = argparse.ArgumentParser(description='Migrate monetary values to minor units')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    args = parser.parse_args()
    
    asyncio.run(run_migration(dry_run=args.dry_run))

if __name__ == '__main__':
    main()
