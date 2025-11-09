import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import EmailValidator
from django.db import models


class Admin(models.Model):
    """Represents an administrator who can receive appointments."""

    id = models.BigIntegerField(primary_key=True, db_index=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80, blank=True)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    phone = models.CharField(max_length=30, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)
    timezone = models.CharField(max_length=64, default="UTC")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["first_name", "last_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class AdminCredential(models.Model):
    """Stores authentication data for an admin."""

    admin = models.OneToOneField(Admin, on_delete=models.CASCADE, related_name="credential")
    password_hash = models.CharField(max_length=128)
    last_login_at = models.DateTimeField(null=True, blank=True)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password_hash)

    def __str__(self) -> str:
        return f"Credential for {self.admin}" if self.admin_id else "Credential (unbound)"
