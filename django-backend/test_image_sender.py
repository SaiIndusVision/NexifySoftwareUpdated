# #!/usr/bin/env python3
# """
# Test Image Sender Script
# Reads images from folder, converts to base64, and sends to streaming API
# """

# import os
# import base64
# import time
# import requests
# import json
# from pathlib import Path

# class ImageSender:
#     def __init__(self, api_url="http://localhost:8000/api/stream-image/"):
#         self.api_url = api_url
#         self.folder_path = "/home/soumya/.nexify/media/sku_images/1/Version1"
#         self.supported_formats = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        
#     def get_image_files(self):
#         """Get all image files from the folder"""
#         if not os.path.exists(self.folder_path):
#             print(f"❌ Folder not found: {self.folder_path}")
#             return []
        
#         image_files = []
#         for filename in os.listdir(self.folder_path):
#             if any(filename.lower().endswith(ext) for ext in self.supported_formats):
#                 image_files.append(os.path.join(self.folder_path, filename))
        
#         return sorted(image_files)
    
#     def image_to_base64(self, image_path):
#         """Convert image file to base64 string"""
#         try:
#             with open(image_path, 'rb') as f:
#                 image_data = f.read()
#                 base64_string = base64.b64encode(image_data).decode('utf-8')
#                 return base64_string
#         except Exception as e:
#             print(f"❌ Error converting {image_path}: {e}")
#             return None
    
#     def send_image(self, base64_image, filename):
#         """Send base64 image to the API"""
#         try:
#             payload = {
#                 "image": base64_image
#             }
            
#             response = requests.post(
#                 self.api_url,
#                 json=payload,
#                 headers={'Content-Type': 'application/json'},
#                 timeout=10
#             )
            
#             if response.status_code == 200:
#                 result = response.json()
#                 print(f"✅ Sent: {filename} (ID: {result.get('image_id', 'unknown')})")
#                 return True
#             else:
#                 print(f"❌ Failed to send {filename}: {response.status_code} - {response.text}")
#                 return False
                
#         except Exception as e:
#             print(f"❌ Error sending {filename}: {e}")
#             return False
    
#     def send_all_images(self, delay=2.0):
#         """Send all images from folder with delay between each"""
#         image_files = self.get_image_files()
        
#         if not image_files:
#             print("❌ No images found in folder")
#             return
        
#         print(f"📁 Found {len(image_files)} images in folder")
#         print(f"📡 Sending to API: {self.api_url}")
#         print(f"⏱️  Delay between images: {delay} seconds")
#         print("-" * 50)
        
#         sent_count = 0
#         failed_count = 0
        
#         for i, image_path in enumerate(image_files, 1):
#             filename = os.path.basename(image_path)
#             print(f"📤 [{i}/{len(image_files)}] Processing: {filename}")
            
#             # Convert to base64
#             base64_image = self.image_to_base64(image_path)
#             if not base64_image:
#                 failed_count += 1
#                 continue
            
#             # Send to API
#             if self.send_image(base64_image, filename):
#                 sent_count += 1
#             else:
#                 failed_count += 1
            
#             # Delay between images (except for the last one)
#             if i < len(image_files):
#                 print(f"⏳ Waiting {delay} seconds...")
#                 time.sleep(delay)
        
#         print("-" * 50)
#         print(f"📊 Summary:")
#         print(f"   ✅ Successfully sent: {sent_count}")
#         print(f"   ❌ Failed: {failed_count}")
#         print(f"   📁 Total images: {len(image_files)}")
        
#     def send_single_image(self, image_name):
#         """Send a single image by name"""
#         image_path = os.path.join(self.folder_path, image_name)
        
#         if not os.path.exists(image_path):
#             print(f"❌ Image not found: {image_path}")
#             return False
        
#         print(f"📤 Sending single image: {image_name}")
        
#         base64_image = self.image_to_base64(image_path)
#         if not base64_image:
#             return False
        
#         return self.send_image(base64_image, image_name)

# def main():
#     """Main function with command line interface"""
#     import sys
    
#     sender = ImageSender()
    
#     print("🎯 Image Sender for Streaming API")
#     print("=" * 50)
    
#     if len(sys.argv) > 1:
#         if sys.argv[1] == "single" and len(sys.argv) > 2:
#             # Send single image
#             image_name = sys.argv[2]
#             sender.send_single_image(image_name)
#         elif sys.argv[1] == "all":
#             # Send all images
#             delay = 2.0
#             if len(sys.argv) > 2:
#                 try:
#                     delay = float(sys.argv[2])
#                 except ValueError:
#                     print("❌ Invalid delay value. Using default 2 seconds.")
#             sender.send_all_images(delay)
#         else:
#             print("❌ Invalid command")
#             print("Usage:")
#             print("  python test_image_sender.py all [delay_seconds]")
#             print("  python test_image_sender.py single <image_name>")
#     else:
#         # Interactive mode
#         print("Choose an option:")
#         print("1. Send all images")
#         print("2. Send single image")
#         print("3. Exit")
        
#         choice = input("Enter your choice (1-3): ").strip()
        
#         if choice == "1":
#             delay = input("Enter delay between images (default 2 seconds): ").strip()
#             try:
#                 delay = float(delay) if delay else 2.0
#             except ValueError:
#                 delay = 2.0
#             sender.send_all_images(delay)
#         elif choice == "2":
#             image_name = input("Enter image filename: ").strip()
#             sender.send_single_image(image_name)
#         elif choice == "3":
#             print("👋 Goodbye!")
#         else:
#             print("❌ Invalid choice")

# if __name__ == "__main__":
#     main()
