# Run this as Administrator to open ports for phone access
# Right-click this file → "Run with PowerShell" → click Yes on UAC prompt

Write-Host "Opening firewall ports for SmartBus..." -ForegroundColor Cyan

# Remove old rules if any
Remove-NetFirewallRule -DisplayName "SmartBus*" -ErrorAction SilentlyContinue

# Allow Metro bundler (JS download)
New-NetFirewallRule -DisplayName "SmartBus Metro 8081" `
    -Direction Inbound -Protocol TCP -LocalPort 8081 -Action Allow -Profile Any | Out-Null

# Allow FastAPI backend
New-NetFirewallRule -DisplayName "SmartBus Backend 8000" `
    -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Any | Out-Null

Write-Host "Done! Firewall rules added for ports 8000 and 8081." -ForegroundColor Green
Write-Host "Now restart Expo (npx expo start --lan) and scan QR again." -ForegroundColor Yellow
pause
