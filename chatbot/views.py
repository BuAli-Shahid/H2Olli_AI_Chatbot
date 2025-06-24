import json
import uuid
import base64
import re
import os
from io import BytesIO
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import openai
from PIL import Image
import cv2
import numpy as np
import pytesseract
from .models import Conversation, Message

# Configure OpenAI
openai.api_key = settings.OPENAI_API_KEY

def extract_text_from_image(image_data):
    """Extract text from image using OCR"""
    try:
        # On Windows, you may need to explicitly point pytesseract to the Tesseract executable.
        # Update this path if you installed Tesseract in a different location.
        tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        # Check if Tesseract executable exists at the specified path
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            print(f"Tesseract executable not found at: {tesseract_path}")
            print("Please ensure Tesseract is installed or update the path in chatbot/views.py.")
            return "OCR_NOT_AVAILABLE"

        # Remove data URL prefix if present
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]

        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))

        # Convert to OpenCV format
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # --- OCR Pre-processing Strategies ---
        # Strategy 1: Grayscale
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        
        # Strategy 2: Binary Thresholding
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # --- Attempt OCR with different strategies ---
        text = ""
        configs = r'--oem 3 --psm 6'  # Assume a single uniform block of text.

        # Attempt 1: With thresholding
        print("Attempting OCR with thresholded image...")
        text = pytesseract.image_to_string(thresh, config=configs)
        
        # Attempt 2: With grayscale (if first failed)
        if len(text.strip()) < 15:  # Heuristic for poor result
            print("First attempt had poor results. Attempting OCR with grayscale image...")
            text = pytesseract.image_to_string(gray, config=configs)
        
        # Attempt 3: With original image (if still fails)
        if len(text.strip()) < 15:
            print("Second attempt had poor results. Attempting OCR with original image...")
            text = pytesseract.image_to_string(opencv_image, config=configs)

        print(f"--- OCR Result ---\n{text}\n--------------------")
        
        if not text.strip():
            print("OCR failed to extract any meaningful text from the image.")
            return "ERROR_PROCESSING_IMAGE"

        return text

    except pytesseract.TesseractNotFoundError:
        print("OCR Error: Tesseract is not installed or not in your PATH.")
        print("Please install Tesseract and add it to your system's PATH, or specify the path in chatbot/views.py.")
        return "OCR_NOT_AVAILABLE"
    except Exception as e:
        print(f"An unexpected error occurred during image processing: {e}")
        import traceback
        traceback.print_exc()
        return "ERROR_PROCESSING_IMAGE"

def extract_water_values(text):
    """Extract water measurement values from OCR text"""
    values = {}
    
    # Common patterns for water measurement values
    patterns = {
        'ph': r'pH[:\s]*([0-9]+\.?[0-9]*)',
        'chlorine': r'(?:free\s+)?chlorine[:\s]*([0-9]+\.?[0-9]*)\s*(?:mg/l|ppm)',
        'total_chlorine': r'total\s+chlorine[:\s]*([0-9]+\.?[0-9]*)\s*(?:mg/l|ppm)',
        'alkalinity': r'alkalinity[:\s]*([0-9]+\.?[0-9]*)\s*(?:mg/l|ppm)',
        'cya': r'(?:cyanuric\s+acid|CYA)[:\s]*([0-9]+\.?[0-9]*)\s*(?:mg/l|ppm)',
        'redox': r'redox[:\s]*([0-9]+\.?[0-9]*)\s*(?:mV|mv)',
        'temperature': r'temperature[:\s]*([0-9]+\.?[0-9]*)\s*°?C',
        'customer_number': r'(PB-[A-Z0-9]+)'
    }
    
    for key, pattern in patterns.items():
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and match.groups():
                values[key] = match.group(1)
        except (IndexError, AttributeError):
            continue
    
    return values

def chat_view(request):
    """Main chat interface view"""
    # Generate a unique session ID for this conversation
    session_id = str(uuid.uuid4())
    return render(request, 'chatbot/chat.html', {'session_id': session_id})

@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    """API endpoint to handle chat messages"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', '')
        image_data = data.get('image_data', None)
        
        # Allow either a message OR an image, but not both empty
        if not user_message and not image_data:
            return JsonResponse({'error': 'Please provide a message or upload an image'}, status=400)
        
        # Get or create conversation
        conversation, created = Conversation.objects.get_or_create(session_id=session_id)
        
        # If no message was provided but image was uploaded, create a default message
        if not user_message and image_data:
            user_message = "📷 I've uploaded an image of my water measurement results. Please analyze it for me."
        
        # Process image if provided
        extracted_data = ""
        if image_data:
            try:
                # Extract text from image
                ocr_text = extract_text_from_image(image_data)
                
                if ocr_text == "OCR_NOT_AVAILABLE":
                    user_message += "\n\n📷 Image uploaded successfully! However, OCR (text recognition) is not available on this system. Please manually enter your water measurement values in the chat, and I'll analyze them for you."
                elif ocr_text == "ERROR_PROCESSING_IMAGE":
                    user_message += "\n\n📷 Image uploaded, but there was an error processing it. Please manually enter your water measurement values in the chat, and I'll analyze them for you."
                elif ocr_text:
                    # Extract water values from OCR text
                    water_values = extract_water_values(ocr_text)
                    
                    # Format extracted data for ChatGPT
                    extracted_data = f"\n\nEXTRACTED DATA FROM UPLOADED IMAGE:\n"
                    extracted_data += f"OCR Text: {ocr_text}\n\n"
                    
                    if water_values:
                        extracted_data += "DETECTED WATER VALUES:\n"
                        for key, value in water_values.items():
                            extracted_data += f"- {key.replace('_', ' ').title()}: {value}\n"
                    else:
                        extracted_data += "No specific water values detected in the image.\n"
                    
                    # Add extracted data to user message
                    user_message += extracted_data
                    
                    # Add a note about image analysis
                    user_message += "\n\nPlease analyze the water values from this image and provide recommendations based on the H2Olli guidelines."
                else:
                    user_message += "\n\n📷 Image uploaded, but no text was detected. Please manually enter your water measurement values in the chat, and I'll analyze them for you."
                
            except Exception as e:
                print(f"Error processing image: {str(e)}")
                user_message += "\n\n📷 Image uploaded, but there was an error processing it. Please manually enter your water measurement values in the chat, and I'll analyze them for you."
        
        # Save user message
        Message.objects.create(
            conversation=conversation,
            role='user',
            content=user_message
        )
        
        # Try to get response from OpenAI API
        try:
            # Get conversation history for context
            messages = conversation.messages.all()
            conversation_history = []
            
            for msg in messages:
                conversation_history.append({
                    'role': msg.role,
                    'content': msg.content
                })
            
            # Prepare messages for OpenAI (keep last 10 messages for context)
            recent_messages = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            
            # Add system message for context
            system_message = {
                'role': 'system',
                'content': '''Chatbot Prompt

This GPT, named H2Olli, is a specialized German-speaking assistant for water analysis, specifically designed for pool owners. It helps to understand and evaluate water values such as pH, free chlorine, total chlorine, alkalinity, cyanuric acid (CYA), and – if available – the redox potential. These values are obtained from a photometer or read directly from existing pool technology.

The customer can upload a photo of their measurement results. H2Olli will recognize the customer number (starting with "PB-"), read out the values, and provide a precise analysis. After extracting the data, H2Olli will specifically ask whether the measured values were correctly identified or if a number might have been misread, to ensure a reliable analysis.

The analysis of the values is based exclusively on the customer number entered or recognized by the customer in the chat. Automatic querying or searching within a customer file via chat is not possible. Only the customer number known and provided by the customer will be used.

Users generally know their own pool technology and may share additional information if needed.

The analysis of test strips is only carried out if a redox, pH, and temperature measurement is also available. Otherwise, H2Olli will point out that a meaningful analysis based on test strips is not possible, as they are too inaccurate. Test strips merely serve to verify existing electronic measurement data. If test strip values deviate from standard values, it will be clearly communicated that an electronic measurement using a photometer is strongly recommended for dosing or making changes to the pool technology.

Note on the Use of Test Strips:

Please note that measurement results from test strips alone are not sufficiently accurate to derive a reliable analysis or concrete dosing recommendations. Therefore, an evaluation will only be carried out if electronic measurement values (redox, pH and temperature) are also available.

If the test strip values deviate from the expected standard values, we strongly recommend an electronic measurement with a photometer before you dose chemicals or make adjustments to your system.

If the electronically measured values for pH, redox, and temperature match the test strips or are within the normal range, only a very brief analysis will be provided with the note that "everything is in order," and an image with the note "Bathing approved" will be displayed.

The target range for free chlorine content is 0.6–1.0 mg/l. If it falls below this, H2Olli recommends adjusting the salt electrolysis production. In case of suspected algae or significantly elevated total chlorine, HTH Shock is specifically recommended to break down combined chlorine or perform disinfection. A chlorine neutralizer is used only in exceptional cases.

If a redox sensor is present, H2Olli interprets the redox value in conjunction with temperature, pH, chlorine availability, and target alkalinity, as well as providing a target value for cyanuric acid (CYA). The redox value is a control variable – it serves as a switching point for activating salt electrolysis or the liquid chlorine pump. The redox value is continuously measured, and if it falls below the set value, chlorine production is automatically adjusted. Therefore, the redox value is not evaluated based on a fixed target range, but in the context of the control strategy of the respective system. If the chlorine value is too high, even though CYA, TA, and pH are within the target range, it is recommended to lower the redox setpoint on the system. If the chlorine value is too low, however, even though CYA, TA, and pH are within the target range, the redox setpoint should be increased accordingly.

The water temperature is derived from the measurement protocol transmitted by the customer and serves as additional information for assessing the redox and pH recommendation. For redox values that are too low or too high in non-automated pools, it provides specific instructions for adjustment – for example, by changing chlorine production, pH correction, or shock treatment with HTH Shock.

Recommendations for alkalinity, pH, or CYA are made taking into account the HTH product line. H2Olli explains the correlations clearly, objectively, and in impeccable English. Communication takes place exclusively in English – both in the analysis, the formulation of recommendations for action, and in the dialogue style.

For pH value corrections upwards, H2Olli allows for a natural pH increase in case of slight deviations and recommends the use of pH-Plus only in exceptional cases of extreme deviations. The target pH recommendation always takes into account the current water temperature and is adjusted accordingly so that customers can make the right setting. An exception applies to PoolCop customers, as their system automatically regulates the pH value adjustment depending on the temperature.

When adding TA+, it is recommended to dose the entire amount at once. For customers with an automatic pH dosing system and measurement, the peristaltic pump should be switched off for 24 hours to avoid counter-dosing in case of a pH increase.

It asks targeted follow-up questions if important information is missing or unclear and refers legal questions to the relevant authorities. The tone is professional, friendly, and geared towards both laypersons and experts.

H2Olli can also work with an uploaded customer list in the format of the file "file-STEACcR7Xp4hdx6sfAaXF5" to automatically integrate filter type, chlorine type, pH regulation, redox measurement, and PoolCop status into recommendations. The prerequisite for this is that the customer enters their exact customer number in the chat. An automatic search or query in this list does not occur.'''
            }
            
            messages_for_openai = [system_message] + recent_messages
            
            # Call OpenAI API using the correct format for version 0.28.1
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=messages_for_openai,
                max_tokens=500,
                temperature=0.7
            )
            
            assistant_response = response.choices[0].message.content
            
        except Exception as api_error:
            print(f"OpenAI API Error: {str(api_error)}")
            # Provide a mock response if API fails
            if "quota" in str(api_error).lower():
                assistant_response = "I'm sorry, but I'm currently experiencing technical difficulties due to API quota limits. Please try again later or contact support to resolve this issue."
            else:
                assistant_response = "I'm sorry, but I'm having trouble connecting to my AI service right now. Please try again in a moment."
        
        # Save assistant response
        Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=assistant_response
        )
        
        return JsonResponse({
            'response': assistant_response,
            'session_id': session_id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Error in send_message: {str(e)}")  # Debug print
        return JsonResponse({'error': str(e)}, status=500) 