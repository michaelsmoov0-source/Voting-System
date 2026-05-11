import os
import json
import logging
import gzip
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.core import serializers
from django.db import connection
from django.conf import settings
from django.utils import timezone
from io import StringIO
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backup voting system data including database, media files, and configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['database', 'media', 'full'],
            default='full',
            help='Type of backup to perform'
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            help='Compress backup files'
        )
        parser.add_argument(
            '--upload-s3',
            action='store_true',
            help='Upload backup to S3'
        )
        parser.add_argument(
            '--retention-days',
            type=int,
            default=30,
            help='Number of days to retain backups'
        )

    def handle(self, *args, **options):
        backup_type = options['type']
        compress = options['compress']
        upload_s3 = options['upload_s3']
        retention_days = options['retention_days']
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f'/tmp/backups/{timestamp}'
        os.makedirs(backup_dir, exist_ok=True)
        
        self.stdout.write(f"Starting {backup_type} backup at {timestamp}")
        
        try:
            if backup_type in ['database', 'full']:
                self.backup_database(backup_dir, compress)
            
            if backup_type in ['media', 'full']:
                self.backup_media(backup_dir, compress)
            
            self.backup_configuration(backup_dir, compress)
            
            if upload_s3:
                self.upload_to_s3(backup_dir, timestamp)
            
            self.cleanup_old_backups(retention_days)
            
            self.stdout.write(
                self.style.SUCCESS(f"Backup completed successfully: {backup_dir}")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Backup failed: {str(e)}")
            )
            logger.error(f"Backup failed: {str(e)}")
            raise

    def backup_database(self, backup_dir, compress):
        """Backup database with all models and relationships"""
        self.stdout.write("Backing up database...")
        
        # Export all models using Django serializers
        from voting.models import (
            Election, Candidate, Vote, AdminMFA, MFAFailedAttempt,
            ElectionResultSnapshot, VoterRegistration, UserIP
        )
        from django.contrib.auth.models import User
        
        models_to_backup = [
            User, Election, Candidate, Vote, AdminMFA, 
            MFAFailedAttempt, ElectionResultSnapshot, 
            VoterRegistration, UserIP
        ]
        
        backup_file = os.path.join(backup_dir, 'database.json')
        
        with open(backup_file, 'w') as f:
            for model in models_to_backup:
                queryset = model.objects.all()
                data = serializers.serialize('json', queryset)
                f.write(f"-- {model.__name__} --\n")
                f.write(data)
                f.write("\n\n")
        
        if compress:
            self.compress_file(backup_file)
            backup_file += '.gz'
        
        self.stdout.write(f"Database backup saved to {backup_file}")

    def backup_media(self, backup_dir, compress):
        """Backup media files and candidate images"""
        self.stdout.write("Backing up media files...")
        
        media_dir = getattr(settings, 'MEDIA_ROOT', '/tmp/media')
        if os.path.exists(media_dir):
            import shutil
            backup_media_dir = os.path.join(backup_dir, 'media')
            shutil.copytree(media_dir, backup_media_dir, dirs_exist_ok=True)
            
            if compress:
                shutil.make_archive(
                    os.path.join(backup_dir, 'media'),
                    'gztar',
                    backup_dir,
                    'media'
                )
                shutil.rmtree(backup_media_dir)
            
            self.stdout.write("Media files backed up successfully")
        else:
            self.stdout.write("No media directory found to backup")

    def backup_configuration(self, backup_dir, compress):
        """Backup configuration and environment variables"""
        self.stdout.write("Backing up configuration...")
        
        config_data = {
            'timestamp': timezone.now().isoformat(),
            'django_settings': {
                'DEBUG': settings.DEBUG,
                'ALLOWED_HOSTS': settings.ALLOWED_HOSTS,
                'DATABASE_ENGINE': settings.DATABASES['default']['ENGINE'],
                'INSTALLED_APPS': settings.INSTALLED_APPS,
                'MIDDLEWARE': settings.MIDDLEWARE,
                'LANGUAGE_CODE': settings.LANGUAGE_CODE,
                'TIME_ZONE': settings.TIME_ZONE,
            },
            'security_settings': {
                'SECURE_SSL_REDIRECT': getattr(settings, 'SECURE_SSL_REDIRECT', False),
                'SESSION_COOKIE_SECURE': getattr(settings, 'SESSION_COOKIE_SECURE', False),
                'CSRF_COOKIE_SECURE': getattr(settings, 'CSRF_COOKIE_SECURE', False),
                'SECURE_HSTS_SECONDS': getattr(settings, 'SECURE_HSTS_SECONDS', 0),
            }
        }
        
        config_file = os.path.join(backup_dir, 'config.json')
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2, default=str)
        
        if compress:
            self.compress_file(config_file)
        
        self.stdout.write("Configuration backed up successfully")

    def compress_file(self, file_path):
        """Compress a file using gzip"""
        with open(file_path, 'rb') as f_in:
            with gzip.open(f"{file_path}.gz", 'wb') as f_out:
                f_out.writelines(f_in)
        os.remove(file_path)

    def upload_to_s3(self, backup_dir, timestamp):
        """Upload backup to S3"""
        self.stdout.write("Uploading backup to S3...")
        
        s3_bucket = os.getenv('AWS_S3_BUCKET')
        s3_region = os.getenv('AWS_S3_REGION', 'us-east-1')
        
        if not s3_bucket:
            self.stdout.write("S3 bucket not configured, skipping upload")
            return
        
        try:
            s3_client = boto3.client('s3')
            
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    local_path = os.path.join(root, file)
                    s3_key = f"backups/{timestamp}/{file}"
                    
                    s3_client.upload_file(
                        local_path,
                        s3_bucket,
                        s3_key,
                        ExtraArgs={
                            'ServerSideEncryption': 'AES256'
                        }
                    )
            
            self.stdout.write(f"Backup uploaded to S3: s3://{s3_bucket}/backups/{timestamp}/")
            
        except (NoCredentialsError, ClientError) as e:
            self.stdout.write(f"S3 upload failed: {str(e)}")
            logger.error(f"S3 upload failed: {str(e)}")

    def cleanup_old_backups(self, retention_days):
        """Clean up old backup files"""
        self.stdout.write(f"Cleaning up backups older than {retention_days} days...")
        
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        backup_base_dir = '/tmp/backups'
        
        if os.path.exists(backup_base_dir):
            for item in os.listdir(backup_base_dir):
                item_path = os.path.join(backup_base_dir, item)
                
                if os.path.isdir(item_path):
                    try:
                        # Extract timestamp from directory name
                        dir_timestamp = datetime.strptime(item, '%Y%m%d_%H%M%S')
                        dir_timestamp = timezone.make_aware(dir_timestamp)
                        
                        if dir_timestamp < cutoff_date:
                            import shutil
                            shutil.rmtree(item_path)
                            self.stdout.write(f"Deleted old backup: {item}")
                            
                    except ValueError:
                        # Skip directories that don't match timestamp format
                        continue
        
        # Clean up S3 backups if configured
        s3_bucket = os.getenv('AWS_S3_BUCKET')
        if s3_bucket:
            try:
                s3_client = boto3.client('s3')
                paginator = s3_client.get_paginator('list_objects_v2')
                
                for page in paginator.paginate(Bucket=s3_bucket, Prefix='backups/'):
                    for obj in page.get('Contents', []):
                        if obj['LastModified'].replace(tzinfo=timezone.utc) < cutoff_date:
                            s3_client.delete_object(Bucket=s3_bucket, Key=obj['Key'])
                            self.stdout.write(f"Deleted old S3 backup: {obj['Key']}")
                            
            except (NoCredentialsError, ClientError) as e:
                self.stdout.write(f"S3 cleanup failed: {str(e)}")
