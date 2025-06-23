import base64
from django.core.files.storage import default_storage

def get_base64_image(image_field):
    if not image_field:
        return ""

    try:
        with default_storage.open(image_field.name, 'rb') as image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:{image_field.file.content_type};base64,{encoded}"
    except Exception as e:
        return ""
