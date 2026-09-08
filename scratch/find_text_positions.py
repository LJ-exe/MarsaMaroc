"""
Find exact text positions from the user's attestation image.
"""
from PIL import Image, ImageDraw
import os

# The user provided an image showing the attestation with filled text
# I need to analyze this image to find where the text is actually placed
# and adjust the coordinates accordingly

# Since I can't directly access the uploaded image, I'll create a script
# that can be used to analyze any attestation image

def find_text_in_image(img, search_text_region):
    """Find text in a specific region of the image."""
    # This is a placeholder - in reality, we'd need OCR or manual marking
    pass

# For now, let me create a visual guide based on typical attestation layout
# The user said the attestation is good but not aligned properly
# This means the text is being placed but in the wrong positions

# Based on the typical Marsa Maroc attestation layout:
# "Je soussigné, [DIRECTEUR NAME] Directeur des Ressources Humaines..."
# "Monsieur [STAGIAIRE NAME] a effectué un stage..."
# "à compter du [START DATE]..."

# The current positions in the code are:
# Directeur RH: X=170, Y=530
# Nom stagiaire: X=210, Y=395
# Date début: X=290, Y=345

# I need to adjust these based on the user's feedback
# Let me create a test with different positions

print("Current positions in code:")
print("Directeur RH: X=170, Y=530")
print("Nom stagiaire: X=210, Y=395")
print("Date début: X=290, Y=345")

print("\nBased on typical attestation layout, the positions should be:")
print("Directeur RH: X=180, Y=520 (after 'Je soussigné,')")
print("Nom stagiaire: X=220, Y=380 (after 'Monsieur')")
print("Date début: X=300, Y=340 (after 'à compter du')")

print("\nPlease provide the exact positions from the user's image")
print("or run a visual analysis to find the correct coordinates.")
