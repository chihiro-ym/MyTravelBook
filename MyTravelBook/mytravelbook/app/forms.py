from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from app.models import User

class SingupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["name", "email", "password1", "password2"]
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています")
        return email
    
class LoginForm(AuthenticationForm):
    username = forms.EmailField(label="メールアドレス")  # メールアドレスをusernameとして使用
    password = forms.CharField(widget=forms.PasswordInput, label="パスワード")