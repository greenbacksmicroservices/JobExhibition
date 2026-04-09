import os

from django.apps import apps
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, Storage
from django.urls import reverse


class DatabaseMediaStorage(Storage):
    """
    Store uploaded media in the database while keeping read compatibility
    with older files present in MEDIA_ROOT.
    """

    def __init__(self):
        self._filesystem = FileSystemStorage(
            location=getattr(settings, "MEDIA_ROOT", ""),
            base_url=getattr(settings, "MEDIA_URL", "/media/"),
        )

    @staticmethod
    def _model():
        return apps.get_model("dashboard", "StoredMediaAsset")

    @staticmethod
    def _normalize_name(name):
        value = (name or "").replace("\\", "/").strip()
        return value.lstrip("/")

    def _save(self, name, content):
        normalized_name = self._normalize_name(name)
        available_name = self.get_available_name(normalized_name)
        payload = content.read()
        if not isinstance(payload, bytes):
            payload = bytes(payload or b"")
        model = self._model()
        model.objects.update_or_create(
            file_key=available_name,
            defaults={
                "original_name": os.path.basename(getattr(content, "name", "") or available_name),
                "content": payload,
                "content_type": (getattr(content, "content_type", "") or "").strip(),
                "size": len(payload),
            },
        )
        return available_name

    def _open(self, name, mode="rb"):
        normalized_name = self._normalize_name(name)
        model = self._model()
        asset = model.objects.filter(file_key=normalized_name).only("content").first()
        if asset:
            return ContentFile(bytes(asset.content or b""), name=normalized_name)
        return self._filesystem._open(normalized_name, mode)

    def delete(self, name):
        normalized_name = self._normalize_name(name)
        model = self._model()
        model.objects.filter(file_key=normalized_name).delete()
        if self._filesystem.exists(normalized_name):
            self._filesystem.delete(normalized_name)

    def exists(self, name):
        normalized_name = self._normalize_name(name)
        model = self._model()
        if model.objects.filter(file_key=normalized_name).exists():
            return True
        return self._filesystem.exists(normalized_name)

    def size(self, name):
        normalized_name = self._normalize_name(name)
        model = self._model()
        asset = model.objects.filter(file_key=normalized_name).only("size").first()
        if asset:
            return int(asset.size or 0)
        return self._filesystem.size(normalized_name)

    def url(self, name):
        normalized_name = self._normalize_name(name)
        model = self._model()
        if model.objects.filter(file_key=normalized_name).exists():
            return reverse("dashboard:db_media_file", kwargs={"file_key": normalized_name})
        return self._filesystem.url(normalized_name)
