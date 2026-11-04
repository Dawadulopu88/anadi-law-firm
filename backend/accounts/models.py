from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import UserManager


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        LAWYER = 'lawyer', 'Lawyer'
        STAFF = 'staff', 'Staff'
        CLIENT = 'client', 'Client'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CLIENT)
    phone = models.CharField(max_length=20, blank=True)

    objects = UserManager()

    def __str__(self):
        return self.get_full_name() or self.username
