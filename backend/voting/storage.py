import os
import uuid
from urllib.parse import urlparse


def _get_client():
    from supabase import create_client

    supabase_url = os.getenv("SUPABASE_URL", "")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not service_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured.")
    return create_client(supabase_url, service_key)


def _bucket_name() -> str:
    return os.getenv("SUPABASE_BUCKET_NAME", "candidate-images")


def upload_candidate_image(file_obj, election_id: int) -> str:
    client = _get_client()
    bucket = _bucket_name()
    ext = os.path.splitext(file_obj.name)[1].lower() or ".jpg"
    path = f"election-{election_id}/{uuid.uuid4().hex}{ext}"
    content = file_obj.read()
    client.storage.from_(bucket).upload(path, content, {"content-type": file_obj.content_type, "upsert": "true"})
    return client.storage.from_(bucket).get_public_url(path)


def delete_candidate_image_by_url(url: str) -> None:
    if not url:
        return
    parsed = urlparse(url)
    marker = "/storage/v1/object/public/"
    if marker not in parsed.path:
        return
    _, tail = parsed.path.split(marker, 1)
    if "/" not in tail:
        return
    bucket, path = tail.split("/", 1)
    if not path:
        return
    client = _get_client()
    client.storage.from_(bucket).remove([path])
