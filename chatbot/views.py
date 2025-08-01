
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
    """
    Extract customer ID from message text.
    Supports various formats like:
    - "pb-10001"
    - "here is my id pb-10001"
    - "my customer id is pb-10001"
    - "pb10001"
    - "PB-10001"
    - "10001"
    """
    if not message:
        return None

    # Convert to lowercase for case-insensitive matching
    message_lower = message.lower().strip()

    # Pattern 1: pb-xxxxx format (with or without hyphen, case insensitive)
    pattern1 = r'\bpb-?(\d+)\b'
    match1 = re.search(pattern1, message_lower)
    if match1:
        number = match1.group(1)
        return f"pb-{number}"  # Always return with hyphen format

    # Pattern 2: Explicit customer ID mentions
    pattern2 = r'(?:customer[_\s]*id|id)[:\s]+([a-zA-Z0-9-_]+)'
    match2 = re.search(pattern2, message_lower)
    if match2:
        potential_id = match2.group(1)
        # If it's just numbers, add pb- prefix
        if potential_id.isdigit():
            return f"pb-{potential_id}"
        return potential_id

    # Pattern 3: Just a number that looks like a customer ID (4-6 digits) - ONLY if message is very short
    words = message_lower.split()
    if len(words) <= 3:  # Only check if message is short
        pattern3 = r'\b(\d{4,6})\b'
        match3 = re.search(pattern3, message_lower)
        if match3:
            number = match3.group(1)
            return f"pb-{number}"

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
    """API endpoint to handle chat messages - supports multiple images"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4()))

        # Handle both single image (backward compatibility) and multiple images
        image_data_list = []
        single_image = data.get('image_data', None)
        if single_image:
            image_data_list.append(single_image)
        multiple_images = data.get('images', [])
        if multiple_images and isinstance(multiple_images, list):
            image_data_list.extend(multiple_images)

        # Initialize assistant_response
        assistant_response = "I'm sorry, I couldn't process your request at this time."

        # Allow either a message OR images, but not both empty
        if not user_message and not image_data_list:
            return JsonResponse({'error': 'Please provide a message or upload at least one image'}, status=400)

        # Limit number of images
        max_images = 5
        if len(image_data_list) > max_images:
            return JsonResponse({'error': f'Maximum {max_images} images allowed per request'}, status=400)

        # FIRST: Check for customer ID (only for text-only requests)
        customer_id = None
        if user_message and not image_data_list:
            customer_id = is_customer_id(user_message)
            print(f"Debug: Original message: '{user_message}'")
            print(f"Debug: Extracted customer ID: '{customer_id}'")

        # SECOND: Handle customer ID requests
        if customer_id:
            print(f"Debug: Processing customer ID: {customer_id}")

            # Get pool data for this customer
            pool_result = get_pool_data_for_customer(customer_id)

            if pool_result.get('status') != 200:
                error_message = pool_result.get('error', 'Unknown error occurred')
                assistant_response = f"I'm sorry, but I couldn't retrieve the pool data for customer ID '{customer_id}'. Error: {error_message}"
            else:
                # Format pool data for AI analysis
                pool_data = pool_result['data']
                formatted_data = format_pool_data_for_analysis(pool_data)

                system_message = {
                    'role': 'system',
                    'content': '''You are H2Olli, a specialized professional assistant for comprehensive pool water analysis. You help pool owners understand and evaluate water conditions to determine if their pool is safe for swimming.

                **Current Request**: Analyze real-time pool monitoring data retrieved from a customer's pool monitoring system.

                **Water Parameters You Analyze:**
                - pH levels, Free Chlorine, Total Chlorine, Alkalinity (Total Alkalinity/TA)
                - Cyanuric Acid (CYA), Redox potential (ORP/mV), Water temperature

                **Water Quality Standards:**
                - pH: 7.2-7.6 (optimal), 7.0-7.8 (acceptable)
                - Free Chlorine: 1.0-3.0 mg/L (ppm)
                - Total Alkalinity: 80-120 mg/L (ppm)
                - Cyanuric Acid: 30-50 mg/L (ppm)

                **DETAILED RESPONSE REQUIREMENTS FOR CUSTOMER DATA:**

                1. **Data Summary**: "Based on the live monitoring data for customer ID [ID], here are the current readings..."

                2. **Comprehensive Parameter Analysis**: 
                   - Evaluate each parameter against optimal ranges
                   - Explain what each parameter does for pool safety and water balance
                   - Mention any interactions between parameters (e.g., pH affects chlorine effectiveness)
                   - Note any missing parameters that should be monitored
                   - Discuss how current readings compare to ideal ranges

                3. **Detailed Swimming Safety Assessment**: 
                   - Clear verdict: "SAFE FOR SWIMMING" or "NOT RECOMMENDED FOR SWIMMING"
                   - Comprehensive explanation of why it's safe or unsafe based on the data
                   - Potential health implications if any parameters are out of range
                   - Special considerations (skin/eye sensitivity, children, extended swimming sessions)
                   - Current conditions vs. ideal conditions analysis
                   - Risk assessment for different types of swimmers

                4. **Specific Recommendations**: 
                   - Immediate actions needed (if any) with step-by-step instructions
                   - Preventive maintenance suggestions to maintain good water quality
                   - When to retest specific parameters
                   - What additional parameters to monitor
                   - Chemical adjustment calculations if needed

                5. **Professional Insights**:
                   - How current levels will trend over time based on usage and weather
                   - Environmental factors that might affect these levels (temperature, rain, bather load)
                   - Best practices for maintaining current good levels
                   - Signs to watch for that indicate changes are needed
                   - Seasonal considerations for pool maintenance

                6. **Equipment and Monitoring Tips**:
                   - How the monitoring system helps maintain water quality
                   - Benefits of continuous monitoring vs manual testing
                   - When to calibrate or check monitoring equipment
                   - Backup testing recommendations

                7. **Safety and Maintenance Reminders**:
                   - General swimming safety guidelines
                   - When to avoid swimming despite good chemistry readings
                   - How often to test water manually as backup
                   - Pool maintenance schedule recommendations

                **IMPORTANT**: Always provide detailed, professional explanations even when parameters are within optimal ranges. Users want to understand WHY their pool is safe, not just that it is safe. Include educational information about water chemistry interactions and maintenance best practices. Make the response comprehensive and informative.

                Always prioritize swimmer safety and provide professional, actionable advice with thorough explanations.'''
                }

                try:
                    # Call OpenAI API for customer data analysis
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            system_message,
                            {"role": "user", "content": formatted_data}
                        ],
                        max_tokens=1200,
                        temperature=0.7
                    )
                    assistant_response = response.choices[0].message.content

                except Exception as api_error:
                    print(f"OpenAI API Error: {str(api_error)}")
                    assistant_response = f"""I've retrieved your live pool monitoring data for customer ID '{customer_id}', but I'm having trouble with my AI analysis service. Here's your current pool status:

{formatted_data}

Please consult with a pool professional for proper interpretation of these values."""

        # THIRD: Handle greetings ONLY if no customer ID was detected
        elif user_message and not image_data_list:
            user_lower = user_message.lower().strip()
            greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'help', 'what can you do']

            if any(greeting in user_lower for greeting in greetings):
                assistant_response = """Hello! I'm H2Olli, your pool water analysis assistant. I can help you analyze your pool water to determine if it's safe for swimming. You can:

• Share your water test values (pH, chlorine, alkalinity, etc.)
• Upload images of test strips or digital readings  
• Simply provide your customer ID (like 'pb-xxxxx') to get your live pool monitoring data and instant analysis

How can I help you today?"""

                return JsonResponse({
                    'response': assistant_response,
                    'session_id': session_id,
                    'images_processed': 0
                })
            else:
                # Handle regular text messages (non-greeting, non-customer ID)
                system_message = {
                    'role': 'system',
                    'content': '''You are H2Olli, a specialized professional assistant for comprehensive pool water analysis. You help pool owners understand and evaluate water conditions to determine if their pool is safe for swimming.

**Your Analysis Capabilities:**
1. **Manual Data Entry**: Analyze water values that users type directly
2. **Digital Image Reading**: Extract text and numerical values from uploaded images of digital meters, photometers, or measurement displays
3. **Color Strip Analysis**: Analyze uploaded images of pool test strips by comparing colors to standard color charts and provide approximate readings

**Water Parameters You Analyze:**
- pH levels
- Free Chlorine
- Total Chlorine
- Alkalinity (Total Alkalinity/TA)
- Cyanuric Acid (CYA)
- Redox potential (ORP/mV)
- Water temperature
- Calcium Hardness
- Bromine (if applicable)

**Analysis Process:**
1. **Data Collection**: Carefully read all provided information (manual entry, digital readings, or color strip analysis)
2. **Value Interpretation**: For color strips, compare each color pad to standard test strip color charts and provide estimated ranges
3. **Accuracy Assessment**: For digital readings, ask for confirmation of values. For color strips, mention they provide approximate readings and digital measurements are more precise
4. **Professional Analysis**: Evaluate all parameters against safe swimming standards
5. **Clear Recommendations**: Provide specific guidance on water safety and any needed adjustments

**Water Quality Standards:**
- pH: 7.2-7.6 (optimal), 7.0-7.8 (acceptable)
- Free Chlorine: 1.0-3.0 mg/L (ppm)
- Total Alkalinity: 80-120 mg/L (ppm)
- Cyanuric Acid: 30-50 mg/L (ppm)
- Water Temperature: Monitor for comfort and chemical effectiveness

**Professional Tone:**
- Use clear, professional language
- Provide scientific explanations when helpful
- Be encouraging while emphasizing safety
- Offer practical, actionable advice

**Safety Priority:**
Always prioritize swimmer safety. When in doubt about water quality, recommend professional testing or err on the side of caution.

Remember: You provide educational guidance, but users should follow local health department guidelines and consult pool professionals for complex issues.'''
                }

                try:
                    # Call OpenAI API for regular text message
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            system_message,
                            {"role": "user", "content": user_message}
                        ],
                        max_tokens=800,
                        temperature=0.7
                    )
                    assistant_response = response.choices[0].message.content

                except Exception as api_error:
                    print(f"OpenAI API Error: {str(api_error)}")
                    assistant_response = "I'm sorry, but I'm having trouble connecting to my AI service right now. Please try again in a moment."

        # FOURTH: Handle images or messages with images
        else:
            # If no message was provided but images were uploaded, create a default message
            if not user_message and image_data_list:
                if len(image_data_list) == 1:
                    user_message = "📷 I've uploaded an image of my water measurement results. Please analyze it for me."
                else:
                    user_message = f"📷 I've uploaded {len(image_data_list)} images of my water measurement results. Please analyze them for me."

            # System message for image analysis
            system_message = {
                'role': 'system',
                'content': '''You are H2Olli, a specialized professional assistant for comprehensive pool water analysis. You help pool owners understand and evaluate water conditions to determine if their pool is safe for swimming.

**Your Analysis Capabilities:**
1. **Manual Data Entry**: Analyze water values that users type directly
2. **Digital Image Reading**: Extract text and numerical values from uploaded images of digital meters, photometers, or measurement displays
3. **Color Strip Analysis**: Analyze uploaded images of pool test strips by comparing colors to standard color charts and provide approximate readings

**Multiple Image Analysis:**
- When analyzing multiple images, examine each image separately and identify what type of measurement it shows
- Compare readings across multiple images to identify any inconsistencies
- If multiple test strips are shown, analyze each one and note any variations
- For digital displays, read each device's measurements carefully
- Provide a comprehensive analysis combining all available data

**Water Parameters You Analyze:**
- pH levels, Free Chlorine, Total Chlorine, Alkalinity (Total Alkalinity/TA)
- Cyanuric Acid (CYA), Redox potential (ORP/mV), Water temperature
- Calcium Hardness, Bromine (if applicable)

**Color Strip Analysis Instructions:**
- Identify each color pad on the test strip(s)
- Compare colors to standard pool test strip color charts
- Provide estimated readings with appropriate ranges (e.g., "pH appears to be approximately 7.2-7.4 based on the color")
- Note any difficulty in reading specific colors due to lighting or image quality
- If multiple strips are shown, compare results and note any variations
- Recommend digital testing for precise measurements when needed

**DETAILED RESPONSE REQUIREMENTS FOR IMAGE ANALYSIS:**

1. **Image Summary**: "I can see [X] image(s) showing [detailed description of what's in each image]..."

2. **Comprehensive Data Summary**: "Based on your color strip analysis/digital readings, here are the detected values..." (Include estimated ranges and confidence levels)

3. **Detailed Parameter Analysis**: 
   - Evaluate each parameter against optimal ranges with thorough explanations
   - Explain what each parameter does for pool safety and water balance
   - Discuss interactions between parameters (e.g., pH affects chlorine effectiveness)
   - Compare current readings to ideal ranges with specific explanations
   - Note any missing parameters that should be monitored

4. **Comprehensive Swimming Safety Assessment**: 
   - Clear verdict: "SAFE FOR SWIMMING" or "NOT RECOMMENDED FOR SWIMMING"
   - Detailed explanation of why it's safe or unsafe based on ALL detected parameters
   - Potential health implications if any parameters are out of range
   - Special considerations for different swimmers (children, sensitive skin, extended sessions)
   - Risk assessment and safety margins

5. **Detailed Specific Recommendations**: 
   - Step-by-step instructions for any needed chemical adjustments
   - Exact chemical amounts and application methods
   - Order of chemical additions (what to add first, waiting times)
   - How to calculate chemical dosages based on pool size
   - When and how to retest after adjustments
   - Alternative treatment options if primary chemicals aren't available

6. **Professional Insights and Best Practices**:
   - How current levels will trend over time with normal use
   - Environmental factors affecting these readings (weather, bather load, etc.)
   - Preventive maintenance to avoid future imbalances
   - Signs to watch for indicating water chemistry changes
   - Seasonal considerations and adjustments
   - Equipment maintenance that affects water chemistry

7. **Testing and Monitoring Guidance**:
   - Limitations of test strip readings vs digital testing
   - When to use professional testing services
   - Recommended testing frequency for each parameter
   - How to improve test strip accuracy (timing, lighting, technique)
   - Backup testing methods and cross-verification

8. **Additional Professional Guidance**:
   - Pool maintenance schedule recommendations
   - Chemical storage and safety tips
   - When to consult pool professionals
   - Common mistakes to avoid
   - Cost-effective maintenance strategies

**Water Quality Standards:**
- pH: 7.2-7.6 (optimal), 7.0-7.8 (acceptable)
- Free Chlorine: 1.0-3.0 mg/L (ppm)
- Total Alkalinity: 80-120 mg/L (ppm)
- Cyanuric Acid: 30-50 mg/L (ppm)

**IMPORTANT**: Provide detailed, educational explanations for every recommendation. Users want to understand not just WHAT to do, but WHY they need to do it, HOW to do it properly, and WHEN to expect results. Make responses comprehensive and informative, treating each analysis as a complete professional consultation.

Always prioritize swimmer safety and provide thorough, actionable advice with complete explanations.'''
            }

            # Build the user content with text and ALL images
            user_content = []
            if user_message:
                user_content.append({"type": "text", "text": user_message})

            # Add ALL images to the content array
            for i, image_data in enumerate(image_data_list):
                # If image_data is a base64 string, convert to data URL
                if not image_data.startswith("data:image"):
                    image_data = f"data:image/png;base64,{image_data}"
                user_content.append({"type": "image_url", "image_url": {"url": image_data}})
                print(f"Debug: Added image {i + 1} of {len(image_data_list)} to analysis")

            try:
                # Call OpenAI API with vision support
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        system_message,
                        {"role": "user", "content": user_content}
                    ],
                    max_tokens=1500,  # Increased for more detailed responses
                    temperature=0.7
                )
                assistant_response = response.choices[0].message.content

            except Exception as api_error:
                print(f"OpenAI API Error: {str(api_error)}")
                print(f"Error type: {type(api_error)}")
                import traceback
                traceback.print_exc()

                # Provide specific error messages based on error type
                if "quota" in str(api_error).lower():
                    assistant_response = "I'm sorry, but I'm currently experiencing technical difficulties due to API quota limits. Please try again later or contact support to resolve this issue."
                elif "authentication" in str(api_error).lower() or "unauthorized" in str(api_error).lower():
                    assistant_response = "I'm sorry, but there's an authentication issue with the AI service. Please check the API configuration."
                elif "model" in str(api_error).lower():
                    assistant_response = "I'm sorry, but the requested AI model is not available. Please try again later."
                else:
                    assistant_response = "I'm sorry, but I'm having trouble connecting to my AI service right now. Please try again in a moment."

        # Return response
        return JsonResponse({
            'response': assistant_response,
            'session_id': session_id,
            'images_processed': len(image_data_list)
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Error in send_message: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)