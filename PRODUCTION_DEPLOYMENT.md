# Production Deployment Guide

This guide covers deploying the Secure Electronic Voting System to production with all security, monitoring, and performance optimizations.

## 🚀 Production Environment Setup

### 1. Environment Variables

Copy `.env.production.example` to `.env` and configure all required variables:

```bash
cp .env.production.example .env
# Edit .env with your actual values
```

**Critical Variables:**
- `DJANGO_SECRET_KEY`: Generate with `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- `DATABASE_URL`: Your Supabase connection string
- `ADMIN_API_KEY`: Generate secure random string
- `ADMIN_INVITE_KEY`: Generate secure random string

### 2. Database Setup

#### Database Configuration (PostgreSQL Only)
# Option 1: Use DATABASE_URL (preferred)
DATABASE_URL=postgresql://username:password@host:5432/postgres

# Option 2: Use individual database variables (required if no DATABASE_URL)
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-postgres-password
DB_HOST=host
DB_PORT=5432

# Note: SQLite is not supported. PostgreSQL is required for all environments.

#### Database Migration:
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 3. Security Configuration

#### SSL/TLS Setup:
- Ensure `SECURE_SSL_REDIRECT=True` in production
- Configure HSTS headers for browser security
- Set up SSL certificates (handled automatically by Vercel)

#### CORS Configuration:
```python
CORS_ALLOWED_ORIGINS = [
    "https://your-domain.vercel.app",
    "https://your-custom-domain.com"
]
```

## 📊 Monitoring and Logging

### Health Checks

System provides three monitoring endpoints:

1. **Health Check**: `/health/` - Basic system health
2. **System Status**: `/status/` - Detailed system metrics
3. **Readiness Probe**: `/ready/` - For container orchestration

### Log Monitoring

Logs are configured for production:
- **Application logs**: JSON format for structured logging
- **Security logs**: Separate file for security events
- **Error logs**: Enhanced error tracking

#### Log Locations:
- Application: `/tmp/django.log`
- Security: `/tmp/security.log`

### Performance Monitoring

Key metrics to monitor:
- Response times (target: <200ms for 95th percentile)
- Database connection pool usage
- Memory usage (alert at 85%)
- Disk space (alert at 85%)
- Rate limiting metrics

## 🔒 Security Features

### Rate Limiting

Configured rate limits per endpoint:
- **Login**: 5 requests per 5 minutes
- **Register**: 3 requests per 5 minutes  
- **Vote**: 10 requests per hour
- **MFA**: 10 requests per 5 minutes
- **Default**: 100 requests per hour

### Security Headers

Production security headers:
- HSTS with 1-year max age
- Content Security Policy
- XSS Protection
- Frame Options (DENY)
- Content Type Options

### Authentication Security

- Multi-factor authentication for admins
- Encrypted IP address storage
- Session management with secure cookies
- CSRF protection enabled

## 🗄️ Database Optimization

### Connection Pooling

```python
DATABASES = {
    "default": {
        "CONN_MAX_AGE": 600,  # 10 minutes
        "ATOMIC_REQUESTS": True,
        "OPTIONS": {
            "MAX_CONNS": 20,
            "MIN_CONNS": 5,
            "connect_timeout": 60,
        }
    }
}
```

### Query Optimization

- Database indexes on frequently queried fields
- Query optimization with `select_related` and `prefetch_related`
- Connection pooling for high concurrency

## 🚀 Caching Strategy

### Redis Configuration (Recommended)

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL"),
        "TIMEOUT": 300,  # 5 minutes
    }
}
```

### Cache Usage

- Session storage in cache
- Rate limiting data
- Frequently accessed election data
- API response caching where appropriate

## 💾 Backup and Recovery

### Automated Backups

Run daily backups with cron:

```bash
# Daily at 2 AM
0 2 * * * /path/to/venv/bin/python manage.py backup_system --type full --compress --upload-s3
```

### Backup Types

1. **Database**: All models and relationships
2. **Media**: Candidate images and files
3. **Configuration**: Settings and environment info

### S3 Backup Configuration

```bash
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=your-backup-bucket
AWS_S3_REGION=us-east-1
```

### Recovery Procedure

1. Stop application
2. Restore database from backup
3. Restore media files
4. Update configuration if needed
5. Restart application
6. Verify system health

## 📈 Performance Tuning

### Gunicorn Configuration

```bash
gunicorn config.wsgi:application \
    --workers 4 \
    --worker-class sync \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 30 \
    --keep-alive 5 \
    --bind 0.0.0.0:$PORT
```

### Memory Optimization

- Monitor memory usage with `/status/` endpoint
- Configure appropriate worker processes
- Use connection pooling to reduce memory overhead

### Database Performance

- Monitor slow queries with pg_stat_statements
- Regular vacuum and analyze operations
- Index optimization based on query patterns

## 🔧 Maintenance Tasks

### Daily Tasks

1. **Log Rotation**: Configure logrotate for log files
2. **Backup**: Automated backup execution
3. **Health Monitoring**: Check system health endpoints
4. **Security Review**: Review security logs for suspicious activity

### Weekly Tasks

1. **Performance Review**: Analyze response times and resource usage
2. **Backup Verification**: Test backup restoration process
3. **Security Updates**: Apply security patches
4. **Database Maintenance**: Vacuum and analyze tables

### Monthly Tasks

1. **Capacity Planning**: Review resource usage trends
2. **Security Audit**: Comprehensive security review
3. **Backup Cleanup**: Remove old backups per retention policy
4. **Performance Optimization**: Review and optimize slow queries

## 🚨 Incident Response

### Security Incidents

1. **Immediate**: Block suspicious IPs using rate limiting
2. **Investigation**: Review security logs for attack patterns
3. **Containment**: Isolate affected systems if needed
4. **Recovery**: Restore from clean backup if compromised
5. **Post-mortem**: Document incident and improvements

### System Outages

1. **Detection**: Monitor health check endpoints
2. **Assessment**: Use `/status/` endpoint for system diagnostics
3. **Resolution**: Restart services or restore from backup
4. **Communication**: Notify stakeholders of outage and resolution

## 📋 Deployment Checklist

### Pre-deployment

- [ ] Environment variables configured
- [ ] Database migrations tested
- [ ] SSL certificates valid
- [ ] Backup procedures tested
- [ ] Monitoring endpoints configured
- [ ] Security headers verified
- [ ] Rate limiting tested
- [ ] Cache configuration validated

### Post-deployment

- [ ] Health checks passing
- [ ] Database connectivity verified
- [ ] Cache functionality working
- [ ] Authentication flows tested
- [ ] Security monitoring active
- [ ] Performance metrics baseline established
- [ ] Backup schedule configured
- [ ] Error monitoring verified

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check `DATABASE_URL` format
   - Verify Supabase credentials
   - Check network connectivity

2. **High Memory Usage**
   - Review worker process count
   - Check for memory leaks
   - Optimize database queries

3. **Slow Response Times**
   - Check database query performance
   - Verify cache hit rates
   - Review resource constraints

4. **Rate Limiting Issues**
   - Check cache configuration
   - Review rate limit settings
   - Monitor for abuse patterns

### Debug Commands

```bash
# Check system health
curl https://your-domain.com/health/

# View detailed status
curl https://your-domain.com/status/

# Test database connectivity
python manage.py dbshell

# Check migrations
python manage.py showmigrations

# Run backup manually
python manage.py backup_system --type full --compress
```

This production deployment guide ensures your voting system is secure, performant, and maintainable in a production environment.
