# coding:utf-8
from django.conf import settings

from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.hashers import make_password

from market.utils.models import slugify_uniquely

if getattr(settings, "ENABLE_POSTGIS", False):
    from django.contrib.gis.db.models import GeoManager as Manager
else:
    from django.db.models import Manager


class CustomUserManager(BaseUserManager):
    """Manager handling mostly specific emailing stuff."""

    use_in_migrations = True

    def get_or_create_verified(self, defaults={}, **kwargs):
        """Create active and verified user."""
        kwargs.pop("is_active", True)
        user, created = self.get_or_create(defaults, **kwargs)
        self.verify(user)
        return user, created

    def get_or_create(self, defaults={}, **kwargs):
        """Create a new user if similar does not exists yet."""
        password = kwargs.pop("password", None)
        qs = self.filter(**kwargs)
        if qs.exists():
            return (qs.get(), False)
        kwargs["password"] = password  # put back the password
        kwargs.update(defaults)
        return self.create_user(**kwargs), True

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a User with the given name, email and password."""
        if not extra_fields.get('slug', None):
            if 'name' in extra_fields:
                slug_base = extra_fields['name']
            else:
                slug_base = email.split("@")[0]
            slug = slugify_uniquely(self.model, slug_base)
        extra_fields.update(is_superuser=False, is_staff=False)

        user = self.model(email=email, slug=slug, **extra_fields)
        user.password = make_password(password)  # is password is None => unusable password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """Create superuser - verified by default."""
        user = self.create_verified_user(email, password, **extra_fields)
        user.is_staff = True
        user.is_active = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

    def create_verified_user(self, **kwargs):
        """Create verified user."""
        user = self.create_user(**kwargs)
        return self.verify(user)
    create_verified = create_verified_user

    def verify(self, user):
        """Verify user within account app."""
        from allauth.account import utils as account_utils
        from allauth.account import models as account_models

        account_utils.sync_user_email_addresses(user)
        email = account_models.EmailAddress.objects.get(user=user)
        email.verified = True
        email.primary = True
        email.save(using=self._db)
        user.is_active = True
        user.save(using=self._db)
        return user


class ActiveManager(Manager):
    """For models having `active` field."""

    def active(self):
        """Supply `all()` but select only active models."""
        return self.get_queryset().filter(active=True)


class ActiveCategoryManager(ActiveManager):
    """Manager for models having a category and `active` feild."""

    def within(self, category):
        """Select only active instances within certain category."""
        return (self.active()
                .filter(category_id__gte=category.gte)
                .filter(category_id__lt=category.lt)
                .filter(active=True))


class CategoryManager(Manager):
    """Manager for models having a category."""

    def within(self, category):
        """Select only active instances within certain category."""
        return (self.all()
                .filter(category_id__gte=category.gte)
                .filter(category_id__lt=category.lt)
                .filter(active=True))
