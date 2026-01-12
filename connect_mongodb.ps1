# MongoDB Atlas Connection Setup Script for PowerShell
# Run this script to set up your MongoDB connection

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MongoDB Atlas Connection Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Your credentials from MongoDB Atlas
$username = "adnanshaikhyder_db_user"
$password = "DrNezBg3XE7nb5bt"
$database = "apexwealth"

Write-Host "Your credentials:" -ForegroundColor Yellow
Write-Host "  Username: $username"
Write-Host "  Password: $password"
Write-Host "  Database: $database"
Write-Host ""

# Get cluster URL from user
Write-Host "Please enter your MongoDB Atlas cluster URL:" -ForegroundColor Yellow
Write-Host "(You can find this in MongoDB Atlas -> Connect -> Connect your application)" -ForegroundColor Gray
Write-Host "Example: cluster0.abc123.mongodb.net" -ForegroundColor Gray
$cluster = Read-Host "Cluster URL"

if ([string]::IsNullOrWhiteSpace($cluster)) {
    Write-Host "Error: Cluster URL is required!" -ForegroundColor Red
    exit 1
}

# Construct connection string
$connectionString = "mongodb+srv://${username}:${password}@${cluster}/${database}?retryWrites=true&w=majority"

Write-Host ""
Write-Host "Setting environment variable..." -ForegroundColor Yellow

# Set for current session
$env:MONGODB_URI = $connectionString

# Also set permanently for user
[System.Environment]::SetEnvironmentVariable('MONGODB_URI', $connectionString, 'User')

Write-Host ""
Write-Host "✅ MongoDB connection string set!" -ForegroundColor Green
Write-Host ""
Write-Host "Connection string:" -ForegroundColor Cyan
Write-Host $connectionString -ForegroundColor Gray
Write-Host ""

# Test connection
Write-Host "Testing connection..." -ForegroundColor Yellow
try {
    python -c "
import sys
import os
sys.path.insert(0, 'apex-wealth-agents')
from database.mongodb_service import get_mongodb_service
mongodb = get_mongodb_service()
if mongodb.is_connected():
    print('✅ Successfully connected to MongoDB Atlas!')
    print(f'   Database: {mongodb.database_name}')
else:
    print('⚠️  Could not connect to MongoDB')
    print('   Please check your credentials and network access')
"
} catch {
    Write-Host "⚠️  Could not test connection automatically" -ForegroundColor Yellow
    Write-Host "   You can test it by starting the application:" -ForegroundColor Gray
    Write-Host "   python apex-wealth-agents\start_server.py" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start the application: python apex-wealth-agents\start_server.py" -ForegroundColor White
Write-Host "2. Check connection: curl http://localhost:8000/database/status" -ForegroundColor White
Write-Host "3. Your IP (49.43.90.160) should already be whitelisted" -ForegroundColor White
Write-Host ""
