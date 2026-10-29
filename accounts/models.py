from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required.')
        account = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        account.set_password(password)
        account.full_clean()
        account.save(using=self._db)
        return account

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        if not extra_fields['is_staff'] or not extra_fields['is_superuser']:
            raise ValueError('A superuser must have staff and superuser permissions.')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        TEACHER = 'teacher', 'Teacher'
        ACCOUNTANT = 'accountant', 'Accountant'
        LIBRARIAN = 'librarian', 'Librarian'
        PARENT = 'parent', 'Parent'
        STUDENT = 'student', 'Student'

    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ADMIN)
    student = models.ForeignKey('students.Student', null=True, blank=True, on_delete=models.PROTECT, related_name='accounts')
    staff = models.ForeignKey('hr.Staff', null=True, blank=True, on_delete=models.PROTECT, related_name='accounts')
    parent = models.ForeignKey('students.Guardian', null=True, blank=True, on_delete=models.PROTECT, related_name='accounts')
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower('email'), name='accounts_user_email_ci_unique'),
            models.CheckConstraint(condition=~Q(role='student') | Q(student__isnull=False), name='accounts_student_link_required'),
            models.CheckConstraint(condition=~Q(role='teacher') | Q(staff__isnull=False), name='accounts_teacher_link_required'),
            models.CheckConstraint(condition=~Q(role='parent') | Q(parent__isnull=False), name='accounts_parent_link_required'),
        ]

    def clean(self):
        super().clean()
        self.email = self.email.lower()
        for role, field in [('student', 'student'), ('teacher', 'staff'), ('parent', 'parent')]:
            if self.role == role and not getattr(self, field + '_id'):
                raise ValidationError({field: 'A linked record is required for this role.'})

    def __str__(self):
        return self.name or self.email


class AccessSession(models.Model):
    token_hash = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='access_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)


class LoginAttempt(models.Model):
    ip = models.GenericIPAddressField(db_index=True)
    at = models.DateTimeField(auto_now_add=True, db_index=True)
