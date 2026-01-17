#!/bin/bash
set -e
echo "Setting up Nginx Reverse Proxy..."

# Install Nginx
sudo apt install -y nginx

# Create Config including large client header buffers
cat <<EOF | sudo tee /etc/nginx/sites-available/ai-tutor
server {
    listen 80;
    server_name _;

    # Allow large file uploads (default is 1MB)
    client_max_body_size 50M;

    # Frontend (Port 3000)
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    # Backend API (Port 8000)
    location /api/v1 {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        
        # Increase timeouts for long AI requests
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
    }
}
EOF

# Enable Site
sudo ln -sf /etc/nginx/sites-available/ai-tutor /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and Restart
sudo nginx -t
sudo systemctl restart nginx
echo "Nginx Setup Complete."
