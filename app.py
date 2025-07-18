import streamlit as st
from PIL import Image
import io
import os
from pathlib import Path
import numpy as np

# ===========================================
# Configuration - Amazon DSP Specifications
# ===========================================

AMAZON_DSP_SPECS = {
    # Desktop Formats
    "Desktop Medium Rectangle": (300, 250, 40),  # (width, height, max_size_kb)
    "Desktop Leaderboard": (728, 90, 40),
    "Desktop Wide Skyscraper": (160, 600, 40),
    "Desktop Large Rectangle": (300, 600, 50),
    "Desktop Billboard": (1940, 500, 200),
    
    # Mobile Formats
    "Mobile Leaderboard": (640, 100, 50),
    "Mobile Detail Banner": (828, 250, 100),
    "Mobile Medium Rectangle": (600, 500, 40),
    "Mobile Leaderboard Tablet": (1456, 180, 200)
}

# ===========================================
# Image Processing Functions
# ===========================================

def check_image_specs(image, file):
    """
    Vérifie si l'image correspond aux spécifications Amazon DSP
    Args:
        image: Image PIL
        file: Fichier uploadé
    Returns:
        tuple: (format_name, size_kb, max_size) ou (None, size_kb, None) si non conforme
    """
    width, height = image.size
    
    # Obtenir la taille directe du fichier uploadé
    file.seek(0, os.SEEK_END)
    size_kb = file.tell() / 1024
    file.seek(0)
    
    for format_name, (req_width, req_height, max_size) in AMAZON_DSP_SPECS.items():
        if (width == req_width and height == req_height):
            return format_name, size_kb, max_size
    return None, size_kb, None

def resize_image(image, target_width, target_height, max_size_kb):
    """
    Redimensionne l'image tout en respectant la limite de poids
    Args:
        image: Image PIL
        target_width: Largeur cible
        target_height: Hauteur cible
        max_size_kb: Poids maximum autorisé
    Returns:
        tuple: (bytes de l'image, format de sortie)
    """
    resized = image.resize((target_width, target_height), Image.LANCZOS)
    img_byte_arr = io.BytesIO()
    
    if resized.mode != 'RGB':
        resized = resized.convert('RGB')
    
    output_format = 'JPEG' if image.format in ['JPEG', 'JPG'] else 'PNG'
    
    if output_format == 'JPEG':
        quality = 95
        while quality > 5:
            img_byte_arr.seek(0)
            img_byte_arr.truncate()
            resized.save(img_byte_arr, format='JPEG', quality=quality, optimize=True)
            current_size = len(img_byte_arr.getvalue()) / 1024
            
            if current_size <= max_size_kb:
                break
            quality -= 5
    else:
        resized.save(img_byte_arr, format='PNG', optimize=True, compression_level=9)
        
        if len(img_byte_arr.getvalue()) / 1024 > max_size_kb:
            img_byte_arr = io.BytesIO()
            resized = resized.convert('RGB')
            quality = 95
            while quality > 5:
                img_byte_arr.seek(0)
                img_byte_arr.truncate()
                resized.save(img_byte_arr, format='JPEG', quality=quality, optimize=True)
                if len(img_byte_arr.getvalue()) / 1024 <= max_size_kb:
                    output_format = 'JPEG'
                    break
                quality -= 5
    
    img_byte_arr.seek(0)
    return img_byte_arr.getvalue(), output_format

def compress_image(image, max_size_kb):
    """
    Compresse l'image pour atteindre le poids maximum autorisé
    Args:
        image: Image PIL
        max_size_kb: Poids maximum autorisé
    Returns:
        bytes: Image compressée
    """
    img_byte_arr = io.BytesIO()
    
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    output_format = 'JPEG' if image.format in ['JPEG', 'JPG'] else 'PNG'
    final_bytes = None
    
    if output_format == 'JPEG':
        quality = 95
        while quality > 5:
            img_byte_arr.seek(0)
            img_byte_arr.truncate()
            image.save(img_byte_arr, format='JPEG', quality=quality, optimize=True)
            if len(img_byte_arr.getvalue()) / 1024 <= max_size_kb:
                final_bytes = img_byte_arr.getvalue()
                break
            quality -= 5
    else:
        min_size = float('inf')
        best_bytes = None
        
        for compression in range(9, -1, -1):
            temp_buffer = io.BytesIO()
            image.save(temp_buffer, format='PNG', optimize=True, compression_level=compression)
            current_size = len(temp_buffer.getvalue()) / 1024
            
            if current_size <= max_size_kb and current_size < min_size:
                min_size = current_size
                best_bytes = temp_buffer.getvalue()
            
            if current_size <= max_size_kb:
                break
        
        if best_bytes is None:
            quality = 95
            while quality > 5:
                img_byte_arr.seek(0)
                img_byte_arr.truncate()
                image.save(img_byte_arr, format='JPEG', quality=quality, optimize=True)
                if len(img_byte_arr.getvalue()) / 1024 <= max_size_kb:
                    best_bytes = img_byte_arr.getvalue()
                    output_format = 'JPEG'
                    break
                quality -= 5
        
        final_bytes = best_bytes
    
    return final_bytes if final_bytes is not None else img_byte_arr.getvalue()

# ===========================================
# Interface Streamlit
# ===========================================

def main():
    """Fonction principale de l'interface utilisateur"""
    st.title("Amazon DSP Creative Scanner")
    
    st.write("Please upload JPG/JPEG or PNG files")
    
    uploaded_files = st.file_uploader("Upload your creative files", 
                                    accept_multiple_files=True,
                                    type=['jpg', 'jpeg', 'png'])
    
    if uploaded_files:
        found_formats = set()
        issues = []
        
        # Traitement de chaque fichier uploadé
        for file in uploaded_files:
            image = Image.open(file)
            format_name, size_kb, max_size = check_image_specs(image, file)
            original_name = os.path.splitext(file.name)[0]
            
            if format_name:
                # Format correct trouvé
                found_formats.add(format_name)
                dimensions = AMAZON_DSP_SPECS[format_name][:2]
                
                st.write(f"✅ {original_name} matches {format_name} ({dimensions[0]}x{dimensions[1]}) - Size: {size_kb:.1f}KB")
                
                # Vérification du poids
                if size_kb > max_size:
                    st.warning(f"⚠️ File size ({size_kb:.1f}KB) exceeds {max_size}KB limit")
                    if st.button(f"Compress {original_name}"):
                        compressed_bytes = compress_image(image, max_size)
                        st.download_button(
                            label="Download compressed image",
                            data=compressed_bytes,
                            file_name=f"{original_name}_compressed.{image.format.lower()}",
                            mime=f"image/{image.format.lower()}"
                        )
            else:
                # Format non conforme
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format=image.format)
                current_size = len(img_byte_arr.getvalue()) / 1024
                
                # Recherche du format le plus proche
                closest_match = None
                min_diff = float('inf')
                
                for spec_name, (req_w, req_h, max_w) in AMAZON_DSP_SPECS.items():
                    w_diff = abs(image.size[0] - req_w)
                    h_diff = abs(image.size[1] - req_h)
                    if w_diff + h_diff < min_diff:
                        min_diff = w_diff + h_diff
                        closest_match = (spec_name, req_w, req_h, max_w)
                
                if closest_match:
                    needs_compression = current_size > closest_match[3]
                    
                    # Message d'erreur approprié
                    if needs_compression:
                        st.error(f"❌ {original_name} doesn't match any dimension and exceeds maximum file weight")
                    else:
                        st.error(f"❌ {original_name} doesn't match any dimension")
                    
                    st.write(f"Closest format: {closest_match[0]} ({closest_match[1]}x{closest_match[2]}) - Max size: {closest_match[3]}KB")
                    
                    # Bouton approprié selon les besoins
                    button_text = f"Resize and compress {original_name}" if needs_compression else f"Resize {original_name}"
                    
                    if st.button(button_text):
                        resized_image = image.resize((closest_match[1], closest_match[2]), Image.LANCZOS)
                        
                        if needs_compression:
                            final_bytes = compress_image(resized_image, closest_match[3])
                            suffix = "resized_compressed"
                            output_format = 'JPEG' if image.format in ['JPEG', 'JPG'] else 'PNG'
                        else:
                            final_bytes, output_format = resize_image(image, closest_match[1], closest_match[2], closest_match[3])
                            suffix = "resized"
                        
                        st.download_button(
                            label=f"Download {suffix} image",
                            data=final_bytes,
                            file_name=f"{original_name}_{suffix}.{output_format.lower()}",
                            mime=f"image/{output_format.lower()}"
                        )
        
        # Affichage des formats manquants
        missing_formats = set(AMAZON_DSP_SPECS.keys()) - found_formats
        if missing_formats:
            st.write("\n### Missing Creatives")
            st.write("The following creative dimensions are missing:")
            for format_name in missing_formats:
                w, h, _ = AMAZON_DSP_SPECS[format_name]
                st.write(f"- {format_name} ({w}x{h})")
            
            # Message pour l'advertiser
            client_message = """Dear Advertiser,

Some creative dimensions are missing for your Amazon DSP campaign. Please provide the following dimensions:

{}

Best regards,""".format("\n".join(f"- {format_name} ({AMAZON_DSP_SPECS[format_name][0]}x{AMAZON_DSP_SPECS[format_name][1]}px)" 
                               for format_name in missing_formats))
            
            st.text_area("Message for client", client_message, height=200)

if __name__ == "__main__":
    main()
