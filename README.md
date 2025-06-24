# H2Olli - Water Analysis Chatbot

A specialized Django-based chatbot for pool water analysis, designed to help pool owners understand and evaluate their water values.

## Features

- **AI-Powered Analysis**: Uses GPT-4o for intelligent water analysis
- **Image Recognition**: Upload photos of measurement results for automatic data extraction
- **OCR Technology**: Extracts text and water values from uploaded images
- **Conversation History**: Maintains context across chat sessions
- **Modern UI**: Beautiful, responsive chat interface
- **Real-time Responses**: Instant AI responses with typing indicators

## Water Analysis Capabilities

H2Olli can analyze and provide recommendations for:
- pH levels
- Free chlorine content
- Total chlorine levels
- Alkalinity
- Cyanuric acid (CYA)
- Redox potential
- Temperature
- Customer numbers (PB- format)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd CHATBOT
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Tesseract OCR (Optional but Recommended)**
   
   For Windows:
   - Download from: https://github.com/UB-Mannheim/tesseract/wiki
   - Install to default location (C:\Program Files\Tesseract-OCR)
   - Add to PATH environment variable
   
   For Linux:
   ```bash
   sudo apt-get install tesseract-ocr
   ```
   
   For Mac:
   ```bash
   brew install tesseract
   ```

5. **Configure OpenAI API Key**
   
   Add your OpenAI API key to `chatbot_project/settings.py`:
   ```python
   OPENAI_API_KEY = 'your-api-key-here'
   ```

6. **Run migrations**
   ```bash
   python manage.py migrate
   ```

7. **Start the server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   
   Open your browser and go to: http://127.0.0.1:8000

## Usage

### Basic Chat
- Type your water analysis questions directly in the chat
- H2Olli will respond with professional analysis and recommendations

### Image Upload
1. Click the "📷 Upload Photo" button
2. Select an image of your measurement results
3. The system will automatically:
   - Extract text from the image using OCR
   - Identify water measurement values
   - Provide analysis based on the extracted data

### Supported Image Types
- Photos of measurement devices
- Screenshots of digital displays
- Scanned measurement reports
- Any image containing water measurement data

## Technical Details

### Backend Technologies
- **Django 4.2.7**: Web framework
- **OpenAI GPT-4o**: AI language model
- **OpenCV**: Image processing
- **Tesseract OCR**: Text extraction from images
- **Pillow**: Image manipulation

### Frontend Technologies
- **HTML5/CSS3**: Modern, responsive design
- **JavaScript**: Real-time chat functionality
- **Base64 Encoding**: Image data transmission

### Database
- **SQLite**: Lightweight database for conversation storage
- **Django ORM**: Object-relational mapping

## File Structure

```
CHATBOT/
├── chatbot/                 # Main app
│   ├── models.py           # Database models
│   ├── views.py            # Backend logic & API endpoints
│   └── urls.py             # URL routing
├── chatbot_project/        # Project settings
│   ├── settings.py         # Django configuration
│   └── urls.py             # Main URL configuration
├── templates/              # HTML templates
│   └── chatbot/
│       └── chat.html       # Main chat interface
├── static/                 # Static files
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## API Endpoints

- `GET /`: Main chat interface
- `POST /api/send-message/`: Send message and receive AI response
  - Supports text messages and image uploads
  - Returns JSON response with AI analysis

## Error Handling

The system gracefully handles:
- Missing Tesseract OCR installation
- Image processing errors
- API quota limits
- Network connectivity issues
- Invalid image formats

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For technical support or questions about water analysis, please contact the development team. 