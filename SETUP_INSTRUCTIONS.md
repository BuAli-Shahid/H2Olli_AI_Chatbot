# H2Olli Backend Setup Instructions

## For Backend Developer (You)

### 1. Start the Django Server
```bash
# Navigate to your project directory
cd "F:\desktop things\Django\CHATBOT"

# Activate virtual environment
.venv\Scripts\activate

# Start the server
python manage.py runserver
```

### 2. Verify Server is Running
- Open browser and go to: `http://127.0.0.1:8000`
- You should see the H2Olli chat interface
- Server runs on port 8000 by default

### 3. Test API Endpoint
- Use Postman or curl to test: `POST http://127.0.0.1:8000/api/send-message/`
- Send a test message to verify it's working

## For Frontend Developer

### 1. Network Configuration
The backend runs on `http://127.0.0.1:8000` (localhost, port 8000)

### 2. CORS Configuration
The backend has CORS enabled, so frontend can connect from:
- `http://localhost:3000` (React default)
- `http://localhost:8080` (Vue default)
- `http://localhost:4200` (Angular default)
- Any other localhost port

### 3. Connection Requirements
- Both computers must be on the same network (same WiFi/LAN)
- Backend server must be running
- Frontend must use the correct IP address (not localhost)

## Network Setup for Different Computers

### Option 1: Same Network (Recommended)
1. **Find your computer's IP address**:
   ```bash
   # On Windows
   ipconfig
   
   # Look for IPv4 Address (usually 192.168.x.x)
   ```

2. **Start server with your IP**:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

3. **Frontend developer uses your IP**:
   ```
   http://YOUR_IP_ADDRESS:8000/api/send-message/
   ```
   Example: `http://192.168.1.100:8000/api/send-message/`

### Option 2: Port Forwarding (Advanced)
If computers are on different networks, you'll need port forwarding on your router.

### Option 3: Cloud Deployment (Production)
For production, deploy to:
- Heroku
- DigitalOcean
- AWS
- Google Cloud

## Testing Connection

### 1. Backend Developer Test
```bash
# Test from your computer
curl -X POST http://127.0.0.1:8000/api/send-message/ \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","message":"Hello"}'
```

### 2. Frontend Developer Test
```javascript
// Test from frontend developer's computer
fetch('http://YOUR_IP_ADDRESS:8000/api/send-message/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    session_id: 'test-session',
    message: 'Hello from frontend!'
  })
})
.then(response => response.json())
.then(data => console.log('Success:', data))
.catch(error => console.error('Error:', error));
```

## Troubleshooting

### Common Issues:

1. **Connection Refused**:
   - Check if Django server is running
   - Verify port 8000 is not blocked by firewall
   - Try different port: `python manage.py runserver 0.0.0.0:8001`

2. **CORS Errors**:
   - Backend has CORS enabled, but check if frontend URL is allowed
   - Add frontend URL to CORS settings if needed

3. **Network Issues**:
   - Ensure both computers are on same network
   - Check Windows Firewall settings
   - Try disabling firewall temporarily for testing

4. **API Not Found**:
   - Verify URL is correct: `/api/send-message/` (with trailing slash)
   - Check Django server logs for errors

## Security Notes

### Development Only:
- Current setup is for development only
- No authentication required
- CORS allows all origins
- Server runs on HTTP (not HTTPS)

### For Production:
- Add authentication
- Use HTTPS
- Configure CORS properly
- Add rate limiting
- Use environment variables for sensitive data

## Support Contact

If the frontend developer has issues:
1. Check if server is running
2. Verify IP address and port
3. Test with curl/Postman first
4. Check Django server logs for errors
5. Ensure both computers are on same network 