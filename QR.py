import cv2
import numpy as np
from pyzbar.pyzbar import decode
import jwt
import json
import os
import re
from fpdf import FPDF
import configparser

processed_images = {}  # Dictionary to keep track of processed images

def sanitize_for_filename(text):
    return re.sub(r'[\/:*?"<>|]', '_', text)

def image_to_pdf(image_path, pdf_filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.image(image_path, x=10, y=10, w=190)
    pdf.output(pdf_filename)

def load_configuration(config_file):
    config = configparser.ConfigParser()
    if not os.path.exists(config_file):
        print(f"Configuration file '{config_file}' does not exist. Creating with default values.")
        config["Directories"] = {"input_directory": "", "save_directory": ""}
        with open(config_file, 'w') as configfile:
            config.write(configfile)
    config.read(config_file)
    return config

def preprocess_image(image):
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply thresholding (example: simple binary thresholding)
        _, thresholded = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
        
        return thresholded
    except Exception as e:
        print(f"Error occurred during image preprocessing: {e}")

def process_image(image_path, save_directory, input_directory):
    try:
        image_name = os.path.basename(image_path)
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Unable to load the image from '{image_path}'")
            return

        # Preprocess the image
        preprocessed_image = preprocess_image(image)

        # Decode the QR code
        decoded_objects = decode(preprocessed_image)

        if not decoded_objects:
            print(f"No QR code detected in the image '{image_name}'")
            return

        for obj in decoded_objects:
            try:
                data = obj.data.decode('utf-8')
                decoded_data = jwt.decode(data, algorithms=["HS256"], options={"verify_signature": False})
                data_dict = json.loads(decoded_data['data'])
                invoice_no = data_dict.get('DocNo', 'N/A')
                date = data_dict.get('DocDt', 'N/A')
                sanitized_invoice_no = sanitize_for_filename(invoice_no)
                sanitized_date = sanitize_for_filename(date)

                os.makedirs(save_directory, exist_ok=True)
                pdf_filename = f"{sanitized_invoice_no}_{sanitized_date}.pdf"
                new_pdf_path = os.path.join(save_directory, pdf_filename)

                # Check if PDF file with the same name already exists
                if os.path.exists(new_pdf_path):
                    print(f"Duplicate Invoice: The invoice '{pdf_filename}' already exists.")
                    os.remove(image_path)  # Remove duplicate image from input directory
                    print(f"Image '{image_name}' deleted from input directory")
                    return  # Skip processing this image

                image_to_pdf(image_path, new_pdf_path)
                print(f"PDF saved as '{pdf_filename}' in '{save_directory}'")

                os.remove(image_path)
                print(f"Image '{image_name}' deleted after processing")
            except jwt.DecodeError as e:
                print(f"Failed to decode token: {e}. Reason: Invalid or corrupted QR code data.")
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON data: {e}. Reason: The decoded QR code data might not be in valid JSON format.")
            except Exception as e:
                print(f"An error occurred while processing QR code data: {e}")
    except Exception as e:
        print(f"An error occurred while decoding QR code: {e}.")

def process_images(config):
    input_directory = config.get("Directories", "input_directory")
    save_directory = config.get("Directories", "save_directory")

    if not input_directory:
        print("Error: Input directory path is empty or invalid.")
        return

    if not os.path.exists(input_directory):
        print(f"Error: Input directory '{input_directory}' does not exist.")
        return

    if not save_directory:
        print("Error: Save directory path is empty or invalid.")
        return

    image_files = [f for f in os.listdir(input_directory) if f.endswith('.jpg')]
    for image_file in image_files:
        image_path = os.path.join(input_directory, image_file)
        process_image(image_path, save_directory, input_directory)

def main():
    default_config_file = "C:\\ProgramData\\Scccannersoft.properties"
    config = load_configuration(default_config_file)
    process_images(config)

if __name__ == "__main__":
    main()