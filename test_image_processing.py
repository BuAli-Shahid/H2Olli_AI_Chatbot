#!/usr/bin/env python
"""
Test script for image processing functionality
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_project.settings')
django.setup()

from chatbot.views import extract_text_from_image, extract_water_values

def test_image_processing():
    """Test the image processing functions"""
    print("🧪 Testing Image Processing Functionality")
    print("=" * 50)
    
    # Test OCR availability
    try:
        import pytesseract
        print("✅ pytesseract is installed")
        
        # Test if Tesseract is available
        try:
            pytesseract.get_tesseract_version()
            print("✅ Tesseract OCR is available")
        except Exception as e:
            print("⚠️  Tesseract OCR is not available: " + str(e))
            print("   You can still use the chatbot, but OCR features will be limited.")
            
    except ImportError:
        print("❌ pytesseract is not installed")
    
    # Test other dependencies
    try:
        import cv2
        print("✅ OpenCV is installed")
    except ImportError:
        print("❌ OpenCV is not installed")
    
    try:
        from PIL import Image
        print("✅ Pillow is installed")
    except ImportError:
        print("❌ Pillow is not installed")
    
    # Test water value extraction
    print("\n🧪 Testing Water Value Extraction")
    print("-" * 30)
    
    test_texts = [
        "pH: 7.2, Free Chlorine: 0.8 mg/l, Total Chlorine: 1.2 mg/l",
        "Alkalinity: 120 ppm, CYA: 50 mg/l, Temperature: 25°C",
        "Redox: 750 mV, Customer: PB-12345",
        "No water values in this text",
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: {text}")
        values = extract_water_values(text)
        if values:
            for key, value in values.items():
                print(f"  ✅ {key}: {value}")
        else:
            print("  ❌ No values detected")
    
    print("\n🎉 Image processing test completed!")
    print("\nTo test with actual images:")
    print("1. Start the server: python manage.py runserver")
    print("2. Open http://127.0.0.1:8000")
    print("3. Upload an image of water measurement results")

if __name__ == "__main__":
    test_image_processing() 