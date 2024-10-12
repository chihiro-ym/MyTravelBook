from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, name, email, password=None):
        if not email:
            raise ValueError("メールアドレスは必須です。")
        email = self.normalize_email(email)
        user = self.model(
            name=name,
            email=email,)
        user.set_password(password)  # パスワードをハッシュ化
        user.save(using=self._db)
        return user
    
    def create_superuser(self, name, email, password=None):
        user = self.create_user(name, email, password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save(using=self._db)
        return user

class User(AbstractUser):
    first_name = None
    last_name = None
    date_joined = None
    username = None
    groups = None
    user_permissions = None
    
    
    name = models.CharField(max_length=64)#unique=True
    email = models.EmailField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ['name']
    
    objects = UserManager()
    
    class Meta:
        db_table = "users"
 
class TravelRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prefecture = models.ForeignKey('Prefecture', on_delete=models.SET_NULL, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=100)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    main_photo_url = models.ImageField(upload_to='photos/', blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    accommodation_info = models.TextField(blank=True, null=True)
    meal_info = models.TextField(blank=True, null=True)
    transport_info = models.TextField(blank=True, null=True)
    cost_info = models.TextField(blank=True, null=True)
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Travel record for {self.user} in {self.prefecture}"
    
class Prefecture(models.Model):
    name = models.CharField(max_length=100, unique=True)
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name