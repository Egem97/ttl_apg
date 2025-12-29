#!/bin/bash

echo "Deploying application..."

# Pull changes from git
git pull origin main

# Rebuild and restart containers
docker-compose down
docker-compose up -d --build

echo "Deployment complete!"
