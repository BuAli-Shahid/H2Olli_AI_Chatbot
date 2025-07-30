# import json
# import uuid
# import base64
# import re
# import os
# from io import BytesIO
# from django.shortcuts import render
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
# from django.conf import settings
# from openai import OpenAI
# from .models import Conversation, Message
# import requests
# from .models import Conversation, Message, PoolCustomer
# # Configure OpenAI client
# client = OpenAI(api_key=settings.OPENAI_API_KEY)
#
# def chat_view(request):
#     """Main chat interface view"""
#     # Generate a unique session ID for this conversation
#     session_id = str(uuid.uuid4())
#     return render(request, 'chatbot/chat.html', {'session_id': session_id})

# @csrf_exempt
# @require_http_methods(["POST"])
# def send_message(request):
#     """API endpoint to handle chat messages"""
#     try:
#         data = json.loads(request.body)
#         user_message = data.get('message', '').strip()
#         session_id = data.get('session_id', '')
#         image_data = data.get('image_data', None)
#
#         # Allow either a message OR an image, but not both empty
#         if not user_message and not image_data:
#             return JsonResponse({'error': 'Please provide a message or upload an image'}, status=400)
#
#         # Get or create conversation
#         conversation, created = Conversation.objects.get_or_create(session_id=session_id)
#
#         # If no message was provided but image was uploaded, create a default message
#         if not user_message and image_data:
#             user_message = "📷 I've uploaded an image of my water measurement results. Please analyze it for me."
#
#         # Save user message
#         Message.objects.create(
#             conversation=conversation,
#             role='user',
#             content=user_message
#         )
#
#         # Try to get response from OpenAI API
#         try:
#             # Debug: Check API key
#             print(f"Debug: API Key starts with: {settings.OPENAI_API_KEY[:10]}...")
#
#             # Get conversation history for context (only text messages for history)
#             messages = conversation.messages.all()
#             conversation_history = []
#
#             for msg in messages:
#                 # Only include text content in conversation history
#                 if msg.role in ['user', 'assistant']:
#                     conversation_history.append({
#                         'role': msg.role,
#                         'content': msg.content
#                     })
#
#             # Prepare messages for OpenAI (keep last 10 messages for context)
#             recent_messages = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
#
#             # Add system message for context
#             system_message = {
#                 'role': 'system',
#                 'content': '''You are H2Olli, a specialized professional assistant for comprehensive pool water analysis. You help pool owners understand and evaluate water conditions to determine if their pool is safe for swimming.
#
# **Your Analysis Capabilities:**
# 1. **Manual Data Entry**: Analyze water values that users type directly
# 2. **Digital Image Reading**: Extract text and numerical values from uploaded images of digital meters, photometers, or measurement displays
# 3. **Color Strip Analysis**: Analyze uploaded images of pool test strips by comparing colors to standard color charts and provide approximate readings
#
# **Water Parameters You Analyze:**
# - pH levels
# - Free Chlorine
# - Total Chlorine
# - Alkalinity (Total Alkalinity/TA)
# - Cyanuric Acid (CYA)
# - Redox potential (ORP/mV)
# - Water temperature
# - Calcium Hardness
# - Bromine (if applicable)
#
# **Analysis Process:**
# 1. **Data Collection**: Carefully read all provided information (manual entry, digital readings, or color strip analysis)
# 2. **Value Interpretation**: For color strips, compare each color pad to standard test strip color charts and provide estimated ranges
# 3. **Accuracy Assessment**: For digital readings, ask for confirmation of values. For color strips, mention they provide approximate readings and digital measurements are more precise
# 4. **Professional Analysis**: Evaluate all parameters against safe swimming standards
# 5. **Clear Recommendations**: Provide specific guidance on water safety and any needed adjustments
#
# **Color Strip Analysis Instructions:**
# - Identify each color pad on the test strip
# - Compare colors to standard pool test strip color charts
# - Provide estimated readings with appropriate ranges (e.g., "pH appears to be approximately 7.2-7.4 based on the color")
# - Note any difficulty in reading specific colors due to lighting or image quality
# - Recommend digital testing for precise measurements when needed
#
# **Response Format:**
# 1. **Data Summary**: "Based on your [manual entry/digital readings/color strip analysis], here are the detected values..."
# 2. **Parameter Analysis**: Evaluate each parameter against optimal ranges
# 3. **Swimming Safety**: Clear verdict - "SAFE FOR SWIMMING" or "NOT RECOMMENDED FOR SWIMMING" with reasons
# 4. **Specific Recommendations**: Detailed steps for any needed corrections
# 5. **Additional Guidance**: General maintenance tips or follow-up suggestions
#
# **Water Quality Standards:**
# - pH: 7.2-7.6 (optimal), 7.0-7.8 (acceptable)
# - Free Chlorine: 1.0-3.0 mg/L (ppm)
# - Total Alkalinity: 80-120 mg/L (ppm)
# - Cyanuric Acid: 30-50 mg/L (ppm)
# - Water Temperature: Monitor for comfort and chemical effectiveness
#
# **Professional Tone:**
# - Use clear, professional language
# - Provide scientific explanations when helpful
# - Be encouraging while emphasizing safety
# - Offer practical, actionable advice
# - Acknowledge limitations of color strip readings when applicable
#
# **Safety Priority:**
# Always prioritize swimmer safety. When in doubt about water quality, recommend professional testing or err on the side of caution. Explain the importance of balanced water chemistry for both safety and equipment protection.
#
# Remember: You provide educational guidance, but users should follow local health department guidelines and consult pool professionals for complex issues.'''
#             }
#
#             # Build the user message for OpenAI
#             user_content = []
#             if user_message:
#                 user_content.append({"type": "text", "text": user_message})
#             if image_data:
#                 # If image_data is a base64 string, convert to data URL
#                 if not image_data.startswith("data:image"):
#                     image_data = f"data:image/png;base64,{image_data}"
#                 user_content.append({"type": "image_url", "image_url": {"url": image_data}})
#
#             # Compose the OpenAI messages array
#             openai_messages = [system_message] + recent_messages
#
#             # Add the new user message (with text and/or image)
#             if len(user_content) > 1:
#                 # Multiple content items (text + image)
#                 openai_messages.append({
#                     "role": "user",
#                     "content": user_content
#                 })
#             else:
#                 # Single content item (text only or image only)
#                 openai_messages.append({
#                     "role": "user",
#                     "content": user_content[0] if user_content else ""
#                 })
#
#             # Debug: Print the messages being sent to OpenAI
#             print(f"Debug: Sending {len(openai_messages)} messages to OpenAI")
#             print(f"Debug: User content has {len(user_content)} items")
#
#             # For text-only messages, use a simpler format
#             if not image_data:
#                 # Text-only conversation
#                 openai_messages = [system_message]
#                 for msg in recent_messages:
#                     openai_messages.append({
#                         "role": msg["role"],
#                         "content": msg["content"]
#                     })
#                 openai_messages.append({
#                     "role": "user",
#                     "content": user_message
#                 })
#             else:
#                 # Vision conversation - ensure proper format
#                 openai_messages = [system_message]
#                 for msg in recent_messages:
#                     openai_messages.append({
#                         "role": msg["role"],
#                         "content": msg["content"]
#                     })
#                 # Add the new user message with vision content
#                 openai_messages.append({
#                     "role": "user",
#                     "content": user_content
#                 })
#
#             # Call OpenAI API with vision support
#             response = client.chat.completions.create(
#                 model="gpt-4o",
#                 messages=openai_messages,
#                 max_tokens=500,
#                 temperature=0.7
#             )
#
#             assistant_response = response.choices[0].message.content
#
#         except Exception as api_error:
#             print(f"OpenAI API Error: {str(api_error)}")
#             print(f"Error type: {type(api_error)}")
#             import traceback
#             traceback.print_exc()
#             # Provide a mock response if API fails
#             if "quota" in str(api_error).lower():
#                 assistant_response = "I'm sorry, but I'm currently experiencing technical difficulties due to API quota limits. Please try again later or contact support to resolve this issue."
#             elif "authentication" in str(api_error).lower() or "unauthorized" in str(api_error).lower():
#                 assistant_response = "I'm sorry, but there's an authentication issue with the AI service. Please check the API configuration."
#             elif "model" in str(api_error).lower():
#                 assistant_response = "I'm sorry, but the requested AI model is not available. Please try again later."
#             else:
#                 assistant_response = "I'm sorry, but I'm having trouble connecting to my AI service right now. Please try again in a moment."
#
#         # Save assistant response
#         Message.objects.create(
#             conversation=conversation,
#             role='assistant',
#             content=assistant_response
#         )
#
#         return JsonResponse({
#             'response': assistant_response,
#             'session_id': session_id
#         })
#
#     except json.JSONDecodeError:
#         return JsonResponse({'error': 'Invalid JSON'}, status=400)
#     except Exception as e:
#         print(f"Error in send_message: {str(e)}")  # Debug print
#         return JsonResponse({'error': str(e)}, status=500)
#


# # NEW FUNCTION 2: Pool Data Retrieval
# def get_pool_data_for_customer(customer_id):
#     """Fetch pool data for a specific customer ID"""
#     try:
#         customer = PoolCustomer.objects.get(customer_id=customer_id)
#     except PoolCustomer.DoesNotExist:
#         return {'error': 'Customer not found', 'status': 404}
#
#     # Step 1: Get token
#     token_url = 'https://poolcopilot.com/api/v1/token'
#     headers = {'Content-Type': 'application/x-www-form-urlencoded'}
#     data = {'APIKEY': customer.api_key}
#
#     try:
#         token_response = requests.post(token_url, headers=headers, data=data, timeout=30)
#
#         if token_response.status_code != 200:
#             return {'error': 'Token request failed', 'status': 500}
#
#         token_data = token_response.json()
#         token = token_data.get('token')
#
#         if not token:
#             return {'error': 'Token not received', 'status': 500}
#
#         # Step 2: Get status using Bearer token
#         status_url = 'https://poolcopilot.com/api/v1/status'
#         status_headers = {'PoolCop-Token': token}
#
#         status_response = requests.get(status_url, headers=status_headers, timeout=30)
#
#         if status_response.status_code != 200:
#             return {'error': 'Status request failed', 'status': 500}
#
#         status_data = status_response.json()
#         pool_data = status_data.get('PoolCop', {})
#
#         if not pool_data:
#             return {'error': 'No PoolCop data available', 'status': 500}
#
#         temperature = pool_data.get('temperature', {})
#
#         # Format data
#         formatted_data = {
#             'pH': pool_data.get('pH'),
#             'free_chlorine': pool_data.get('chlorine'),
#             'total_chlorine': pool_data.get('total_chlorine'),
#             'alkalinity': pool_data.get('alkalinity'),
#             'cyanuric_acid': pool_data.get('cyanuric_acid'),
#             'redox_orp': pool_data.get('orp'),
#             'water_temperature': temperature.get('water'),
#             'customer_id': customer_id
#
#
#         }
#
#         print(f'formatted_data: {formatted_data}')
#         return {'data': formatted_data, 'status': 200}
#
#     except requests.RequestException as e:
#         return {'error': f'Network error: {str(e)}', 'status': 500}
#     except Exception as e:
#         return {'error': f'Unexpected error: {str(e)}', 'status': 500}
#
#
# # NEW FUNCTION 3: Data Formatting
# def format_pool_data_for_analysis(pool_data):
#     """Format pool data into a readable string for AI analysis"""
#     data_str = f"""Pool Water Analysis Data for Customer ID: {pool_data.get('customer_id', 'Unknown')}
#
# Current Measurements:
# - pH Level: {pool_data.get('pH', 'Not available')}
# - Free Chlorine: {pool_data.get('free_chlorine', 'Not available')} ppm
# - Total Chlorine: {pool_data.get('total_chlorine', 'Not available')} ppm
# - Total Alkalinity: {pool_data.get('alkalinity', 'Not available')} ppm
# - Cyanuric Acid: {pool_data.get('cyanuric_acid', 'Not available')} ppm
# - Redox/ORP: {pool_data.get('redox_orp', 'Not available')} mV
# - Water Temperature: {pool_data.get('water_temperature', 'Not available')}°C
#
# Please analyze these values and determine if the pool water is safe for swimming."""
#
#     return data_str


import json
import uuid
import base64
import re
import os
import requests
from io import BytesIO
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from openai import OpenAI
from .models import PoolCustomer

# Configure OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def chat_view(request):
    """Main chat interface view"""
    # Generate a unique session ID for this conversation
    session_id = str(uuid.uuid4())
    return render(request, 'chatbot/chat.html', {'session_id': session_id})


def is_customer_id(message):
    """Check if the message contains a customer ID pattern"""
    # Clean the message
    message = message.strip()

    # Pattern 1: Explicit customer ID format like "customer_id: 12345" or "customer id 12345"
    explicit_pattern = r'customer[_\s]*id[:\s]*([a-zA-Z0-9-]+)'
    match = re.search(explicit_pattern, message, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 2: Message that ONLY contains a potential customer ID (nothing else)
    # - Must be between 4-20 characters (increased minimum from 3 to 4)
    # - Must be alphanumeric with optional hyphens/underscores
    # - Should match common customer ID patterns
    # - Must NOT contain common pool-related words
    pool_keywords = ['ph', 'chlorine', 'ppm', 'alkalinity', 'temperature', 'pool', 'water', 'safe', 'swim', 'test',
                     'strip', 'analysis', 'reading', 'level', 'my', 'is', 'are', 'the', 'and', 'or', 'to', 'for', 'in',
                     'at', 'on', 'with', 'help', 'hi', 'hello', 'what', 'how', 'can', 'please']

    # Check if it's a customer ID pattern
    if re.match(r'^[a-zA-Z0-9-_]{4,20}$', message):
        message_lower = message.lower()

        # Check if the message doesn't contain any pool-related keywords
        if not any(keyword in message_lower for keyword in pool_keywords):
            # Additional patterns that suggest it's a customer ID:
            # 1. Contains numbers and letters (like pb-10001)
            # 2. Contains hyphens or underscores (common in customer IDs)
            # 3. Is all numbers with at least 4 digits

            has_numbers = bool(re.search(r'\d', message))
            has_letters = bool(re.search(r'[a-zA-Z]', message))
            has_separators = bool(re.search(r'[-_]', message))

            # More specific criteria for customer ID detection
            if (has_numbers and has_letters) or has_separators or (message.isdigit() and len(message) >= 4):
                # Additional check: verify if this could be a real customer ID by checking database
                return message

    return None


def is_valid_customer_id(customer_id):
    """Check if a customer ID exists in the database"""
    try:
        PoolCustomer.objects.get(customer_id=customer_id)
        return True
    except PoolCustomer.DoesNotExist:
        return False


def find_similar_customer_ids(partial_id):
    """Find customer IDs that contain the partial ID"""
    try:
        # Search for customer IDs that contain the partial ID
        similar_customers = PoolCustomer.objects.filter(customer_id__icontains=partial_id)
        return [c.customer_id for c in similar_customers]
    except Exception:
        return []

def get_pool_data_for_customer(customer_id):
    """Fetch pool data for a specific customer ID"""
    try:
        # Debug: Print all existing customer IDs
        all_customers = PoolCustomer.objects.all()
        existing_ids = [c.customer_id for c in all_customers]
        print(f"Debug: Existing customer IDs: {existing_ids}")
        print(f"Debug: Looking for customer ID: '{customer_id}'")

        customer = PoolCustomer.objects.get(customer_id=customer_id)
        print(f"Debug: Found customer: {customer.customer_id}")

    except PoolCustomer.DoesNotExist:
        print(f"Debug: Customer '{customer_id}' not found in database")
        return {
            'error': f'Customer ID "{customer_id}" not found. Available customer IDs: {existing_ids}',
            'status': 404
        }

    # Rest of your existing code remains the same...
    # Step 1: Get token
    token_url = 'https://poolcopilot.com/api/v1/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'APIKEY': customer.api_key}

    try:
        token_response = requests.post(token_url, headers=headers, data=data, timeout=30)

        if token_response.status_code != 200:
            return {'error': 'Token request failed', 'status': 500}

        token_data = token_response.json()
        token = token_data.get('token')

        if not token:
            return {'error': 'Token not received', 'status': 500}

        # Step 2: Get status using Bearer token
        status_url = 'https://poolcopilot.com/api/v1/status'
        status_headers = {'PoolCop-Token': token}

        status_response = requests.get(status_url, headers=status_headers, timeout=30)

        if status_response.status_code != 200:
            return {'error': 'Status request failed', 'status': 500}

        status_data = status_response.json()
        pool_data = status_data.get('PoolCop', {})

        if not pool_data:
            return {'error': 'No PoolCop data available', 'status': 500}

        temperature = pool_data.get('temperature', {})

        # Format data
        formatted_data = {
            'pH': pool_data.get('pH'),
            'free_chlorine': pool_data.get('chlorine'),
            'total_chlorine': pool_data.get('total_chlorine'),
            'alkalinity': pool_data.get('alkalinity'),
            'cyanuric_acid': pool_data.get('cyanuric_acid'),
            'redox_orp': pool_data.get('orp'),
            'water_temperature': temperature.get('water'),
            'customer_id': customer_id
        }

        return {'data': formatted_data, 'status': 200}

    except requests.RequestException as e:
        return {'error': f'Network error: {str(e)}', 'status': 500}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}', 'status': 500}

def format_pool_data_for_analysis(pool_data):
    """Format pool data into a readable string for AI analysis"""
    data_str = f"""Pool Water Analysis Data for Customer ID: {pool_data.get('customer_id', 'Unknown')}

Current Measurements:
- pH Level: {pool_data.get('pH', 'Not available')}
- Free Chlorine: {pool_data.get('free_chlorine', 'Not available')} ppm
- Total Chlorine: {pool_data.get('total_chlorine', 'Not available')} ppm
- Total Alkalinity: {pool_data.get('alkalinity', 'Not available')} ppm
- Cyanuric Acid: {pool_data.get('cyanuric_acid', 'Not available')} ppm
- Redox/ORP: {pool_data.get('redox_orp', 'Not available')} mV
- Water Temperature: {pool_data.get('water_temperature', 'Not available')}°C

Please analyze these values and determine if the pool water is safe for swimming."""

    return data_str


@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    """API endpoint to handle chat messages - no conversation storage"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4()))  # Generate if not provided
        image_data = data.get('image_data', None)

        # Initialize assistant_response to avoid reference errors
        assistant_response = "I'm sorry, I couldn't process your request at this time."

        # Allow either a message OR an image, but not both empty
        if not user_message and not image_data:
            return JsonResponse({'error': 'Please provide a message or upload an image'}, status=400)

        # Check if the user message contains a customer ID
        customer_id = None
        if user_message and not image_data:
            customer_id = is_customer_id(user_message)

        # If customer ID is detected, fetch pool data
        if customer_id:
            print(f"Debug: Customer ID detected: {customer_id}")

            # Get pool data for this customer
            pool_result = get_pool_data_for_customer(customer_id)

            if pool_result.get('status') != 200:
                error_message = pool_result.get('error', 'Unknown error occurred')
                assistant_response = f"I'm sorry, but I couldn't retrieve the pool data for customer ID '{customer_id}'. Error: {error_message}"
            else:
                # Format pool data for AI analysis
                pool_data = pool_result['data']
                formatted_data = format_pool_data_for_analysis(pool_data)

                # System message for customer data analysis
                system_message = {
                    'role': 'system',
                    'content': '''You are H2Olli, a specialized professional assistant for comprehensive pool water analysis. You help pool owners understand and evaluate water conditions to determine if their pool is safe for swimming.

**Current Request**: Analyze real-time pool monitoring data retrieved from a customer's pool monitoring system.

**Water Quality Standards:**
- pH: 7.2-7.6 (optimal), 7.0-7.8 (acceptable)
- Free Chlorine: 1.0-3.0 mg/L (ppm)
- Total Alkalinity: 80-120 mg/L (ppm)
- Cyanuric Acid: 30-50 mg/L (ppm)
- Water Temperature: Monitor for comfort and chemical effectiveness

**Response Format:**
1. **Data Summary**: "Based on the live monitoring data for customer ID [ID], here are the current readings..."
2. **Parameter Analysis**: Evaluate each parameter against optimal ranges
3. **Swimming Safety**: Clear verdict - "SAFE FOR SWIMMING" or "NOT RECOMMENDED FOR SWIMMING" with reasons
4. **Specific Recommendations**: Detailed steps for any needed corrections
5. **Additional Guidance**: Maintenance tips or follow-up suggestions

Always prioritize swimmer safety and provide professional, actionable advice.'''
                }

                try:
                    # Call OpenAI API for customer data analysis
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            system_message,
                            {"role": "user", "content": formatted_data}
                        ],
                        max_tokens=800,
                        temperature=0.7
                    )

                    assistant_response = response.choices[0].message.content

                except Exception as api_error:
                    print(f"OpenAI API Error: {str(api_error)}")
                    # Provide a fallback response with the raw data
                    assistant_response = f"""I've retrieved your live pool monitoring data for customer ID '{customer_id}', but I'm having trouble with my AI analysis service. Here's your current pool status:

{formatted_data}

Please consult with a pool professional for proper interpretation of these values."""

        else:
            # Handle regular messages and images (no conversation history)
            if not user_message and image_data:
                user_message = "📷 I've uploaded an image of my water measurement results. Please analyze it for me."

            try:
                # System message for regular analysis
                system_message = {
                    'role': 'system',
                    'content': '''You are H2Olli, a specialized professional assistant for comprehensive pool water analysis. You help pool owners understand and evaluate water conditions to determine if their pool is safe for swimming.

**Your Analysis Capabilities:**
1. **Manual Data Entry**: Analyze water values that users type directly
2. **Digital Image Reading**: Extract text and numerical values from uploaded images of digital meters, photometers, or measurement displays
3. **Color Strip Analysis**: Analyze uploaded images of pool test strips by comparing colors to standard color charts and provide approximate readings

**Water Parameters You Analyze:**
- pH levels, Free Chlorine, Total Chlorine, Alkalinity (Total Alkalinity/TA)
- Cyanuric Acid (CYA), Redox potential (ORP/mV), Water temperature

**Water Quality Standards:**
- pH: 7.2-7.6 (optimal), 7.0-7.8 (acceptable)
- Free Chlorine: 1.0-3.0 mg/L (ppm)
- Total Alkalinity: 80-120 mg/L (ppm)
- Cyanuric Acid: 30-50 mg/L (ppm)

**Response Format:**
1. **Data Summary**: "Based on your [manual entry/digital readings/color strip analysis], here are the detected values..."
2. **Parameter Analysis**: Evaluate each parameter against optimal ranges
3. **Swimming Safety**: Clear verdict - "SAFE FOR SWIMMING" or "NOT RECOMMENDED FOR SWIMMING" with reasons
4. **Specific Recommendations**: Detailed steps for any needed corrections

Always prioritize swimmer safety and provide professional, actionable advice.'''
                }

                # Build the user message for OpenAI
                if image_data:
                    # Image analysis
                    if not image_data.startswith("data:image"):
                        image_data = f"data:image/png;base64,{image_data}"

                    user_content = [
                        {"type": "text", "text": user_message},
                        {"type": "image_url", "image_url": {"url": image_data}}
                    ]

                    openai_messages = [
                        system_message,
                        {"role": "user", "content": user_content}
                    ]
                else:
                    # Text-only analysis
                    openai_messages = [
                        system_message,
                        {"role": "user", "content": user_message}
                    ]

                # Call OpenAI API
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=openai_messages,
                    max_tokens=500,
                    temperature=0.7
                )

                assistant_response = response.choices[0].message.content

            except Exception as api_error:
                print(f"OpenAI API Error: {str(api_error)}")
                import traceback
                traceback.print_exc()

                # Provide error-specific responses
                if "quota" in str(api_error).lower():
                    assistant_response = "I'm sorry, but I'm currently experiencing technical difficulties due to API quota limits. Please try again later."
                elif "authentication" in str(api_error).lower():
                    assistant_response = "I'm sorry, but there's an authentication issue with the AI service. Please check the API configuration."
                else:
                    assistant_response = "I'm sorry, but I'm having trouble connecting to my AI service right now. Please try again in a moment."

        # Return response without saving to database
        return JsonResponse({
            'response': assistant_response,
            'session_id': session_id
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Error in send_message: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)