import streamlit as st
from PIL import Image
import io
import os
from pathlib import Path
import numpy as np

# Définition des specs Amazon DSP
AMAZON_DSP_SPECS = {
    # Desktop
    "Desktop Medium Rectangle": (300, 250, 40),  # (width, height, max_size_kb)
    "Desktop Leaderboard": (728, 90, 40),
    "Desktop Wide Skyscraper": (160, 600, 40),
    "Desktop Large Rectangle": (300, 600, 50),
    "Desktop Billboard": (1940, 500, 200),
    # Mobile
    "Mobile Leaderboard": (640, 100, 50),
    "Mobile Detail Banner": (828, 250, 100),  # Detail and Search Results page
    "Mobile Medium Rectangle": (600, 500, 40),
    "Mobile Leaderboard Tablet": (1456, 180, 200)
}

def check_image_specs(image, desired_format):
    """Vérifie les specs d'une image"""
    width, height = image.size
    
    # Obtenir la taille du fichier original
    original_buffer = io.BytesIO()
    image.save(original_buffer, format=image.format if image.format else 'JPEG')
    size_kb = len(original_buffer.getvalue()) / 1024
    
    for format_name, (req_width, req_height, max_size) in AMAZON_DSP_SPECS.items():
        if (width == req_width and height == req_height):
            return format_name, size_kb, max_size
    return None, size_kb, None

def resize_image(image, target_width, target_height, desired_format):
    """Redimensionne l'image aux dimensions cibles"""
    resized = image.resize((target_width, target_height), Image.LANCZOS)
    img_byte_arr = io.BytesIO()
    
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    if desired_format == 'JPEG':
        resized.save(img_byte_arr, format='JPEG', quality=95, optimize=True)
    else:
        resized.save(img_byte_arr, format='PNG', optimize=True)
        
    img_byte_arr.seek(0)
    return img_byte_arr

def compress_image(image, max_size_kb, desired_format):
    """Compresse l'image jusqu'à atteindre la taille maximale"""
    quality = 95
    img_byte_arr = io.BytesIO()
    
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    if desired_format == 'JPEG':
        while quality > 5:
            img_byte_arr.seek(0)
            img_byte_arr.truncate()
            image.save(img_byte_arr, format='JPEG', quality=quality, optimize=True)
            if len(img_byte_arr.getvalue()) / 1024 <= max_size_kb:
                break
            quality -= 5
    else:
        # Pour PNG, on utilise une compression maximale
        image.save(img_byte_arr, format='PNG', optimize=True)
    
    img_byte_arr.seek(0)
    return img_byte_arr

def main():
    st.title("Amazon DSP Creative Scanner")
    
    # Sélecteur de format
    desired_format = st.selectbox(
        "Select desired format for creatives:",
        ["JPEG", "PNG"],
        index=0
    )
    
    # Adaptation du type de fichiers acceptés en fonction du format choisi
    accepted_types = ['jpg', 'jpeg'] if desired_format == 'JPEG' else ['png']
    file_format_display = "JPG/JPEG" if desired_format == 'JPEG' else "PNG"
    
    st.write(f"Please upload {file_format_display} files only")
    
    uploaded_files = st.file_uploader(f"Upload your {file_format_display} creative files", 
                                    accept_multiple_files=True,
                                    type=accepted_types)
    
    if uploaded_files:
        found_formats = set()
        issues = []
        
        for file in uploaded_files:
            image = Image.open(file)
            format_name, size_kb, max_size = check_image_specs(image, desired_format)
            original_name = os.path.splitext(file.name)[0]
            
            if format_name:
                found_formats.add(format_name)
                dimensions = AMAZON_DSP_SPECS[format_name][:2]
                
                st.write(f"✅ {original_name} matches {format_name} ({dimensions[0]}x{dimensions[1]}) - Size: {size_kb:.1f}KB")
                
                if size_kb > max_size:
                    st.warning(f"⚠️ File size ({size_kb:.1f}KB) exceeds {max_size}KB limit")
                    if st.button(f"Compress {original_name}"):
                        compressed_bytes = compress_image(image, max_size, desired_format)
                        st.download_button(
                            label="Download compressed image",
                            data=compressed_bytes,
                            file_name=f"{original_name}.{desired_format.lower()}",
                            mime=f"image/{desired_format.lower()}"
                        )
            else:
                st.error(f"❌ {original_name} doesn't match any format")
                closest_match = None
                min_diff = float('inf')
                
                for spec_name, (req_w, req_h, _) in AMAZON_DSP_SPECS.items():
                    w_diff = abs(image.size[0] - req_w)
                    h_diff = abs(image.size[1] - req_h)
                    if w_diff + h_diff < min_diff:
                        min_diff = w_diff + h_diff
                        closest_match = (spec_name, req_w, req_h)
                
                if closest_match:
                    st.write(f"Closest format: {closest_match[0]} ({closest_match[1]}x{closest_match[2]})")
                    if st.button(f"Resize {original_name}"):
                        resized_bytes = resize_image(image, closest_match[1], closest_match[2], desired_format)
                        st.download_button(
                            label="Download resized image",
                            data=resized_bytes,
                            file_name=f"{original_name}.{desired_format.lower()}",
                            mime=f"image/{desired_format.lower()}"
                        )
        
        # Vérification des formats manquants
        missing_formats = set(AMAZON_DSP_SPECS.keys()) - found_formats
        if missing_formats:
            st.write("\n### Missing Formats")
            st.write("The following formats are missing:")
            for format_name in missing_formats:
                w, h, _ = AMAZON_DSP_SPECS[format_name]
                st.write(f"- {format_name} ({w}x{h})")
            
            # Génération du message client
            client_message = """Dear Advertiser,

Some creative formats are missing for your Amazon DSP campaign. Please provide the following formats:

{}

Best regards,""".format("\n".join(f"- {format_name} ({AMAZON_DSP_SPECS[format_name][0]}x{AMAZON_DSP_SPECS[format_name][1]}px)" 
                               for format_name in missing_formats))
            
            st.text_area("Message for client", client_message, height=200)

if __name__ == "__main__":
    main()
