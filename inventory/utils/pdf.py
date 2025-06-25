import base64
from pathlib import Path

def get_base64_image(image_or_path):
    try:
        # Handle Django ImageField or regular path
        file_path = Path(image_or_path.path if hasattr(image_or_path, 'path') else image_or_path)

        if not file_path.exists():
            return ""

        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            file_type = file_path.suffix[1:].lower()  # e.g. 'jpg', 'png'
            return f"data:image/{file_type};base64,{encoded_string}"
    except Exception as e:
        print("🔴 Base64 encode error:", e)
        return ""
