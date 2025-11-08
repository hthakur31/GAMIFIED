# GeoSudoku Deployment Guide

This guide covers deploying GeoSudoku to various production environments.

## 🚀 General Production Setup

### 1. Environment Variables
Create a production `.env` file:
```env
DEBUG=False
SECRET_KEY=your-very-secure-secret-key-here
DATABASE_URL=postgresql://username:password@localhost:5432/geosudoku_prod
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 2. Install Production Dependencies
```bash
pip install gunicorn whitenoise
```

### 3. Database Setup
```bash
# PostgreSQL setup
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo -u postgres createdb geosudoku_prod
sudo -u postgres createuser geosudoku_user
sudo -u postgres psql
```

In PostgreSQL:
```sql
ALTER USER geosudoku_user CREATEDB;
ALTER USER geosudoku_user WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE geosudoku_prod TO geosudoku_user;
\q
```

### 4. Django Setup
```bash
python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser
```

## 🐳 Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "geosudoku.wsgi:application"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://geosudoku:password@db:5432/geosudoku
    depends_on:
      - db
    volumes:
      - ./staticfiles:/app/staticfiles
      - ./media:/app/media

  db:
    image: postgres:13
    environment:
      POSTGRES_DB: geosudoku
      POSTGRES_USER: geosudoku
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data/

volumes:
  postgres_data:
```

### Deploy with Docker
```bash
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic --noinput
docker-compose exec web python manage.py createsuperuser
```

## ☁️ Heroku Deployment

### 1. Heroku Setup
```bash
# Install Heroku CLI
# Create Heroku app
heroku create your-geosudoku-app
heroku addons:create heroku-postgresql:hobby-dev
```

### 2. Procfile
```
web: gunicorn geosudoku.wsgi:application
release: python manage.py migrate
```

### 3. Environment Variables
```bash
heroku config:set DEBUG=False
heroku config:set SECRET_KEY=your-secret-key
heroku config:set ALLOWED_HOSTS=your-app.herokuapp.com
```

### 4. Deploy
```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku main
heroku run python manage.py createsuperuser
```

## 🌐 DigitalOcean Droplet Deployment

### 1. Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3-pip python3-venv nginx postgresql postgresql-contrib supervisor
```

### 2. Application Setup
```bash
# Create app user
sudo adduser geosudoku
sudo usermod -aG sudo geosudoku

# Switch to app user
su - geosudoku

# Clone repository
git clone <your-repo> geosudoku
cd geosudoku

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Gunicorn Configuration
Create `/home/geosudoku/geosudoku/gunicorn.conf.py`:
```python
bind = "127.0.0.1:8000"
workers = 3
user = "geosudoku"
timeout = 120
keepalive = 5
max_requests = 1000
preload_app = True
```

### 4. Supervisor Configuration
Create `/etc/supervisor/conf.d/geosudoku.conf`:
```ini
[program:geosudoku]
command=/home/geosudoku/geosudoku/venv/bin/gunicorn --config /home/geosudoku/geosudoku/gunicorn.conf.py geosudoku.wsgi:application
directory=/home/geosudoku/geosudoku
user=geosudoku
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/geosudoku/geosudoku/logs/gunicorn.log
```

### 5. Nginx Configuration
Create `/etc/nginx/sites-available/geosudoku`:
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location /static/ {
        alias /home/geosudoku/geosudoku/staticfiles/;
    }

    location /media/ {
        alias /home/geosudoku/geosudoku/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6. Enable Services
```bash
sudo ln -s /etc/nginx/sites-available/geosudoku /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start geosudoku
```

## 🔒 SSL/HTTPS Setup with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

## 📊 Monitoring & Maintenance

### 1. Log Monitoring
```bash
# Application logs
tail -f /home/geosudoku/geosudoku/logs/django.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Gunicorn logs
tail -f /home/geosudoku/geosudoku/logs/gunicorn.log
```

### 2. Database Backup
```bash
# Create backup script
#!/bin/bash
pg_dump geosudoku_prod > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 3. Application Updates
```bash
# Update application
cd /home/geosudoku/geosudoku
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo supervisorctl restart geosudoku
```

## 🔧 Performance Optimization

### 1. Database Optimization
```python
# In production.py
DATABASES['default']['OPTIONS'] = {
    'MAX_CONNS': 20,
    'OPTIONS': {
        'MAX_CONNS': 20,
    }
}
```

### 2. Caching with Redis
```bash
sudo apt install redis-server
pip install redis django-redis
```

```python
# In production.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### 3. CDN Setup (Optional)
Configure a CDN like Cloudflare or AWS CloudFront for static files.

## 🚨 Security Checklist

- [ ] DEBUG = False in production
- [ ] Strong SECRET_KEY
- [ ] HTTPS enabled
- [ ] Database password secured
- [ ] ALLOWED_HOSTS configured
- [ ] Security headers enabled
- [ ] Regular backups scheduled
- [ ] Monitoring set up
- [ ] Firewall configured
- [ ] Regular security updates

## 📱 Mobile Optimization

The application is responsive and works on mobile devices. For native mobile apps, consider:
- React Native wrapper
- Progressive Web App (PWA) features
- Mobile-specific optimizations

---

For issues during deployment, check the troubleshooting section in the main README.md file.