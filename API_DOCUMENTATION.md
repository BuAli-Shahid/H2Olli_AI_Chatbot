# H2Olli Chatbot API Documentation

## Base URL
```
http://127.0.0.1:8000
```

## API Endpoints

### 1. Chat Interface (Web UI)
- **URL**: `GET /`
- **Description**: Main chat interface webpage
- **Usage**: Open in browser to access the web chat interface

### 2. Send Message API
- **URL**: `POST /api/send-message/`
- **Description**: Send messages and images to the chatbot
- **Content-Type**: `application/json`

#### Request Body
```json
{
  "session_id": "string (UUID)",
  "message": "string (optional)",
  "image_data": "string (base64 encoded image, optional)"
}
```

#### Response
```json
{
  "response": "string (AI response)",
  "session_id": "string (UUID)"
}
```

#### Error Response
```json
{
  "error": "string (error message)"
}
```

## How to Use the API

### 1. Generate Session ID
- Create a unique session ID (UUID) for each conversation
- Example: `"550e8400-e29b-41d4-a716-446655440000"`

### 2. Send Text Message
```javascript
const response = await fetch('http://127.0.0.1:8000/api/send-message/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    session_id: 'your-session-id',
    message: 'Hello, I need help with my pool water analysis'
  })
});

const data = await response.json();
console.log(data.response); // AI response
```

### 3. Send Image (Base64)
```javascript
// Convert image to base64
const fileReader = new FileReader();
fileReader.onload = async function() {
  const base64Image = fileReader.result;
  
  const response = await fetch('http://127.0.0.1:8000/api/send-message/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: 'your-session-id',
      image_data: base64Image
    })
  });
  
  const data = await response.json();
  console.log(data.response); // AI response with image analysis
};

fileReader.readAsDataURL(imageFile);
```

### 4. Send Both Message and Image
```javascript
const response = await fetch('http://127.0.0.1:8000/api/send-message/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    session_id: 'your-session-id',
    message: 'Please analyze this water measurement',
    image_data: 'base64-encoded-image-string'
  })
});
```

## Important Notes

1. **Session Management**: Use the same session_id for related messages to maintain conversation context
2. **Image Format**: Images should be base64 encoded (data:image/jpeg;base64,...)
3. **Supported Image Types**: JPEG, PNG, GIF
4. **Message Length**: No strict limit, but keep messages reasonable
5. **Image Size**: Large images may take longer to process

## Error Handling

### Common Error Codes
- `400`: Bad Request (missing required fields, invalid JSON)
- `500`: Server Error (internal server issues)

### Example Error Handling
```javascript
try {
  const response = await fetch('http://127.0.0.1:8000/api/send-message/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestData)
  });
  
  if (!response.ok) {
    const errorData = await response.json();
    console.error('API Error:', errorData.error);
    return;
  }
  
  const data = await response.json();
  console.log('Success:', data.response);
  
} catch (error) {
  console.error('Network Error:', error);
}
```

## Testing the API

### Using curl
```bash
# Send text message
curl -X POST http://127.0.0.1:8000/api/send-message/ \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-session","message":"Hello"}'

# Send image (replace with actual base64 string)
curl -X POST http://127.0.0.1:8000/api/send-message/ \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-session","image_data":"data:image/jpeg;base64,/9j/4AAQ..."}'
```

### Using Postman
1. Set method to `POST`
2. Set URL to `http://127.0.0.1:8000/api/send-message/`
3. Set Headers: `Content-Type: application/json`
4. Set Body to raw JSON with your request data

## Features

- **Text Analysis**: Send text messages for water analysis questions
- **Image OCR**: Upload images of water measurement results
- **Conversation History**: Maintains context within a session
- **Water Value Extraction**: Automatically extracts pH, chlorine, alkalinity, etc.
- **AI Recommendations**: Provides professional water treatment advice

## Support

If you encounter issues:
1. Check that the Django server is running on port 8000
2. Verify the API endpoint URL is correct
3. Ensure proper JSON formatting in requests
4. Check network connectivity between frontend and backend 