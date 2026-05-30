"""
app/utils/cloudinary_helper.py
-------------------------------
Cloudinary upload / delete / URL helpers for PSFSLA.

Usage:
    from app.utils.cloudinary_helper import upload_image, delete_image, get_url

    # Upload a FileStorage object
    result = upload_image(file_obj, folder="thumbnails")
    public_id  = result["public_id"]   # store this in DB
    secure_url = result["secure_url"]  # full https URL

    # Delete when replacing / deleting
    delete_image("psfsla/thumbnails/abc123")

    # Build a URL (transformation-aware)
    url = get_url("psfsla/thumbnails/abc123", width=400, height=300, crop="fill")
"""

import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import current_app


# ──────────────────────────────────────────────────────────────
#  Bootstrap (called once from create_app)
# ──────────────────────────────────────────────────────────────

def init_cloudinary(app=None):
    """
    Configure the cloudinary SDK.
    Prefers the CLOUDINARY_URL env-var (set automatically by Render's
    Cloudinary add-on).  Falls back to individual key/secret vars.
    """
    cfg = app.config if app else current_app.config

    cloudinary_url = cfg.get("CLOUDINARY_URL") or os.environ.get("CLOUDINARY_URL")
    if cloudinary_url:
        # cloudinary.config() can parse the full URL automatically
        cloudinary.config(cloudinary_url=cloudinary_url, secure=True)
    else:
        cloudinary.config(
            cloud_name = cfg.get("CLOUDINARY_CLOUD_NAME"),
            api_key    = cfg.get("CLOUDINARY_API_KEY"),
            api_secret = cfg.get("CLOUDINARY_API_SECRET"),
            secure     = True,
        )


# ──────────────────────────────────────────────────────────────
#  Allowed file helpers
# ──────────────────────────────────────────────────────────────

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
FILE_EXTENSIONS  = {"pdf", "ppt", "pptx", "doc", "docx", "xls", "xlsx"}

def _allowed(filename: str, allowed: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


# ──────────────────────────────────────────────────────────────
#  upload_image
# ──────────────────────────────────────────────────────────────

def upload_image(file_obj, folder: str = "general", public_id: str = None) -> dict | None:
    """
    Upload a Werkzeug FileStorage (or any file-like) to Cloudinary.

    Parameters
    ----------
    file_obj  : FileStorage  – the uploaded file from the form
    folder    : str          – Cloudinary sub-folder, e.g. "thumbnails", "avatars"
    public_id : str | None   – optional fixed public_id; auto-generated if None

    Returns
    -------
    dict with at least:
        {
          "public_id":  "psfsla/thumbnails/abc123",
          "secure_url": "https://res.cloudinary.com/...",
          "url":        "http://res.cloudinary.com/...",
          "format":     "jpg",
          "width":      800,
          "height":     600,
        }
    or None on failure.
    """
    if not file_obj or not getattr(file_obj, "filename", None):
        return None

    filename = file_obj.filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Determine resource type
    if ext in IMAGE_EXTENSIONS:
        resource_type = "image"
    elif ext in FILE_EXTENSIONS:
        resource_type = "raw"
    else:
        resource_type = "auto"

    upload_kwargs = {
        "folder":        f"psfsla/{folder}",
        "resource_type": resource_type,
        "overwrite":     True,
        "use_filename":  True,
        "unique_filename": True,
    }
    if public_id:
        upload_kwargs["public_id"] = public_id

    try:
        result = cloudinary.uploader.upload(file_obj, **upload_kwargs)
        return result
    except cloudinary.exceptions.Error as exc:
        current_app.logger.error(f"[Cloudinary] Upload error: {exc}")
        return None


# ──────────────────────────────────────────────────────────────
#  delete_image
# ──────────────────────────────────────────────────────────────

def delete_image(public_id: str, resource_type: str = "image") -> bool:
    """
    Delete an asset from Cloudinary by its public_id.

    Returns True on success, False on failure / if public_id is empty.
    """
    if not public_id:
        return False

    # Never delete the default placeholder images
    if "defaults/" in public_id:
        return False

    try:
        result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        return result.get("result") == "ok"
    except cloudinary.exceptions.Error as exc:
        current_app.logger.error(f"[Cloudinary] Delete error: {exc}")
        return False


# ──────────────────────────────────────────────────────────────
#  get_url  (transformation-aware)
# ──────────────────────────────────────────────────────────────

def get_url(
    public_id: str,
    width: int = None,
    height: int = None,
    crop: str = "fill",
    quality: str = "auto",
    format: str = "auto",
) -> str:
    """
    Build a Cloudinary CDN URL for an asset, optionally with transformations.

    If public_id is already a full https:// URL (legacy data), return it as-is.
    """
    if not public_id:
        return ""

    # Already a full URL (stored before Cloudinary migration)
    if public_id.startswith("http://") or public_id.startswith("https://"):
        return public_id

    transformations = {"quality": quality, "fetch_format": format}
    if width:
        transformations["width"] = width
    if height:
        transformations["height"] = height
    if width or height:
        transformations["crop"] = crop

    return cloudinary.CloudinaryImage(public_id).build_url(**transformations)


# ──────────────────────────────────────────────────────────────
#  Convenience: replace old image and upload new one atomically
# ──────────────────────────────────────────────────────────────

def replace_image(file_obj, old_public_id: str = None, folder: str = "general") -> dict | None:
    """
    Upload a new image and delete the old one (if provided and not a default).

    Returns the Cloudinary result dict, or None if no file was provided.
    """
    result = upload_image(file_obj, folder=folder)
    if result and old_public_id:
        delete_image(old_public_id)
    return result
