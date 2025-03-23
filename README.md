#!/bin/bash

# Update system packages
sudo apt update
sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-dev libmysqlclient-dev build-essential libssl-dev nginx

# Install virtualenv
pip3 install virtualenv

# Create project directory
mkdir ~/skillforge
cd ~/skillforge

# Create and activate virtual environment
virtualenv venv
source venv/bin/activate

# Install Django and dependencies
pip install django djangorestframework django-cors-headers pillow mysqlclient gunicorn

# Create Django project
django-admin startproject skillforge_project .

# Create apps
python manage.py startapp accounts
python manage.py startapp courses

# Create media and static directories
mkdir -p media/course_images
mkdir -p static/css
mkdir -p static/js
mkdir -p static/images

# Setup Gunicorn service
sudo bash -c 'cat > /etc/systemd/system/gunicorn.service << EOL
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/skillforge
ExecStart=/home/ubuntu/skillforge/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/home/ubuntu/skillforge/skillforge.sock skillforge_project.wsgi:application

[Install]
WantedBy=multi-user.target
EOL'

# Configure Nginx
sudo bash -c 'cat > /etc/nginx/sites-available/skillforge << EOL
server {
    listen 80;
    server_name your_domain_or_ip;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /home/ubuntu/skillforge;
    }

    location /media/ {
        root /home/ubuntu/skillforge;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/skillforge/skillforge.sock;
    }
}
EOL'

# Enable the Nginx configuration
sudo ln -s /etc/nginx/sites-available/skillforge /etc/nginx/sites-enabled

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Start Gunicorn
sudo systemctl start gunicorn
sudo systemctl enable gunicorn

echo "Basic server setup completed!"