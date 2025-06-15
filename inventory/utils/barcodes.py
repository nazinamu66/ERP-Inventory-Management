import os
import barcode
from barcode.writer import ImageWriter
from django.conf import settings

def generate_barcode_image(data, filename):
    barcode_class = barcode.get_barcode_class('code128')
    ean = barcode_class(data, writer=ImageWriter())

    output_dir = os.path.join(settings.MEDIA_ROOT, "barcodes")
    os.makedirs(output_dir, exist_ok=True)

    file_path = os.path.join(output_dir, f"{filename}.png")
    ean.save(file_path[:-4])  # Removes .png added by save()

    return os.path.join(settings.MEDIA_URL, "barcodes", f"{filename}.png")
