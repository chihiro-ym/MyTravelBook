from django.shortcuts import render, redirect
from django.views import View
from app.forms import SignupForm, LoginForm, UserEditForm, CustomPasswordChangeForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.urls import reverse_lazy
from .forms import TravelRecordForm
from .models import TravelRecord, Prefecture
class TopView(View):
    def get(self, request):
        return render(request, "top.html")
    
class SignupView(View):
    def get(self, request):
        form = SignupForm()
        return render(request, "signup.html", context={
            "form": form
        })
    def post(self, request):
        print(request.POST)
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('login')
        else:
            error_messages = []
            for field in form:
                for error in field.errors:
                    error_messages.append(error)
            print(error_messages)  # デバッグ用
        return render(request, "signup.html", context={
            "form": form,
            "error_messages": error_messages,  
        })
    
class LoginView(View):
    def get(self, request):
        form = LoginForm()
        return render(request, "login.html", context={
            "form": form
        })
    def post(self, request):
        form = LoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')#メールアドレス  
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home') 
            else:
                form.add_error(None, "メールアドレスまたはパスワードが正しくありません。")
        return render(request, "login.html", context={
            "form": form
            })
        
class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')
            
@login_required
def user_edit(request):
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('mypage')
    else:
        form = UserEditForm(instance=request.user)
    return render(request, 'user_edit.html',context={
            'form':form
            })
    
class CustomPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'password_change.html'
    success_url = reverse_lazy('password_change_done')
    
    def form_valid(self, form):
        
        messages.success(self.request, "パスワードが正常に変更されました。")
        return super().form_valid(form)
    
class CustomPasswordChangeDoneView(View):
    def get(self, request):
        return render(request, 'password_change_done.html')
     
@method_decorator([login_required, never_cache], name='dispatch')
class MypageView(View):
    def get(self, request):
        user = request.user
        return render(request, 'mypage.html',context={
            'user': user
        })

class HomeView(View):
    def get(self, request):
        return render(request, "home.html")
    
@login_required
def create_travel_record(request):
    if request.method == 'POST':
        form = TravelRecordForm(request.POST, request.FILES)
        if form.is_valid():
            travel_record = form.save(commit=False)
            travel_record.user = request.user
            travel_record.save()
            messages.success(request, '旅行記録が正常に追加されました。') 
            return redirect('travel_list')
    else:
        form = TravelRecordForm()
        
    prefectures = Prefecture.objects.all() 
    return render(request, 'create_travel_record.html', context={
        'form': form,
        'messages': messages.get_messages(request),
        'prefectures': prefectures
        
        })
    
@login_required
def travel_list(request):
    travel_records = TravelRecord.objects.all()
    return render(request, 'travel_list.html', {'travel_records': travel_records})
    
