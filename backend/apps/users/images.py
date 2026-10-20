import io
import warnings

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError


@deconstructible
class PrivateProfileStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(file_permissions_mode=0o600, directory_permissions_mode=0o700)

    @property
    def location(self):
        return str(settings.PRIVATE_MEDIA_ROOT)

    def url(self, name):
        raise ValueError("Las imágenes privadas no tienen URL pública.")


def sanitize_profile_image(upload):
    if upload.size > 2 * 1024 * 1024:
        raise ValidationError("La imagen debe ocupar como máximo 2 MiB.")
    raw = upload.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValidationError("La imagen debe ocupar como máximo 2 MiB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValidationError("Solo se admiten imágenes JPEG, PNG o WebP.")
                if not all(1 <= dimension <= 4096 for dimension in image.size):
                    raise ValidationError("La imagen no puede superar 4096 × 4096 píxeles.")
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                image.load()
                oriented = ImageOps.exif_transpose(image)
                has_alpha = "A" in oriented.getbands() or "transparency" in oriented.info
                clean = oriented.convert("RGBA" if has_alpha else "RGB")
                clean.info.clear()
                output = io.BytesIO()
                clean.save(output, format="PNG")
        return ContentFile(output.getvalue(), name="profile.png")
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise ValidationError("El archivo no contiene una imagen válida.") from None
