import streamlit as st
from PIL import Image
import io
import os
from pathlib import Path
import numpy as np
from PIL import Image

# Définition des specs Amazon DSP
AMAZON_DSP_SPECS = {
    # Desktop
    "Desktop Leaderboard": (728, 90, 40),  # (width, height, max_size_kb)
    "Desktop Billboard": (970, 250, 40),
    "Desktop Medium Rectangle": (300, 250, 40),
    "Desktop Wide Skyscraper": (160, 600, 40),
    "Desktop Large Rectangle": (300, 600, 40),
    # Mobile
    "Mobile Leaderboard": (320, 50, 40),
    "Mobile Banner": (320, 480, 40),
    "Mobile Medium Rectangle": (300, 250, 40),
    "Mobile Interstitial": (1940, 500, 40),
}

def check_image_specs(image):
    """Vérifie les specs d'une image"""
    width, height = image.size
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    size_kb = len(img_byte_arr.getvalue()) / 1024
    
    for format_name, (req_width, req_height, max_size) in AMAZON_DSP_SPECS.items():
        if (width == req_width and height == req_height):
            return format_name, size_kb, max_size
    return None, size_kb, None

def resize_image(image, target_width, target_height):
    """Redimensionne l'image aux dimensions cibles"""
    return image.resize((target_width, target_height), Image.LANCZOS)

def compress_image(image, max_size_kb):
    """Compresse l'image jusqu'à atteindre la taille maximale"""
    quality = 95
    img_byte_arr = io.BytesIO()
    
    while quality > 5:
        img_byte_arr.seek(0)
        img_byte_arr.truncate()
        image.save(img_byte_arr, format='PNG', quality=quality)
        if len(img_byte_arr.getvalue()) / 1024 <= max_size_kb:
            break
        quality -= 5
    
    return Image.open(img_byte_arr)

def main():
    st.title("Amazon DSP Creative Scanner")
    
    uploaded_files = st.file_uploader("Upload your creative files", 
                                    accept_multiple_files=True,
                                    type=['png', 'jpg', 'jpeg'])
    
    if uploaded_files:
        found_formats = set()
        issues = []
        
        for file in uploaded_files:
            image = Image.open(file)
            format_name, size_kb, max_size = check_image_specs(image)
            
            if format_name:
                found_formats.add(format_name)
                st.write(f"✅ {file.name} matches {format_name}")
                
                if size_kb > max_size:
                    st.warning(f"⚠️ File size ({size_kb:.1f}KB) exceeds {max_size}KB limit")
                    if st.button(f"Compress {file.name}"):
                        compressed = compress_image(image, max_size)
                        st.download_button(
                            label="Download compressed image",
                            data=io.BytesIO().getvalue(),
                            file_name=f"compressed_{file.name}",
                            mime="image/png"
                        )
            else:
                st.error(f"❌ {file.name} doesn't match any format")
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
                    if st.button(f"Resize {file.name}"):
                        resized = resize_image(image, closest_match[1], closest_match[2])
                        st.download_button(
                            label="Download resized image",
                            data=io.BytesIO().getvalue(),
                            file_name=f"resized_{file.name}",
                            mime="image/png"
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
            client_message = """
            Dear Client,
            
            Some creative formats are missing for your Amazon DSP campaign. Please provide the following formats:
            
            {}
            
            Best regards,
            """.format("\n".join(f"- {format_name} ({AMAZON_DSP_SPECS[format_name][0]}x{AMAZON_DSP_SPECS[format_name][1]}px)" 
                               for format_name in missing_formats))
            
            st.text_area("Message for client", client_message, height=200)

if __name__ == "__main__":
    main()
