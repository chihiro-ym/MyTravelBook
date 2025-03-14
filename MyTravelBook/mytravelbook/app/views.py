from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from app.forms import (SignupForm, LoginForm, UserEditForm, 
CustomPasswordChangeForm, TravelRecordForm, PhotoForm,
TravelMemoForm, TravelSearchForm)
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.urls import reverse_lazy
from .models import TravelRecord, Prefecture, Category, Photo, TravelMemo
import random, base64
from django.http import JsonResponse
from django.core.files.base import ContentFile
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError
from django.db.models import Q

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

@method_decorator([login_required, never_cache], name='dispatch')
class HomeView(View):
    def get(self, request):
        recent_travels = TravelRecord.objects.filter(user=request.user).order_by('-created_at')[:3]
       
        latest_memo = TravelMemo.objects.order_by('-updated_at').first()
        latest_travel_record_id = latest_memo.travel_record.id if latest_memo else None
        
        return render(request, "home.html", context={
            'recent_travels': recent_travels,
            'latest_travel_record_id': latest_travel_record_id, 
        })
        
@login_required
def create_travel_record(request):
    if request.method == 'POST':
        form = TravelRecordForm(request.POST, request.FILES)
        if form.is_valid():
            travel_record = form.save(commit=False)
            travel_record.user = request.user
            travel_record.save()
            messages.success(request, '旅行記録が正常に追加されました。') 
            return redirect('travel_detail',travel_record.id)
        else:
            messages.error(request, 'フォームにエラーがあります。再度お試しください。')
    else:
        form = TravelRecordForm()
        
    prefectures = Prefecture.objects.all() 
    return render(request, 'create_travel_record.html', context={
        'form': form,
        'messages': messages.get_messages(request),
        'prefectures': prefectures
        })
    
def get_random_unvisited_prefecture(user):
    # 訪問済みの都道府県を取得
    visited_prefectures = TravelRecord.objects.filter(user=user).exclude(prefecture__isnull=True).values_list('prefecture__id', flat=True)
    # 未訪問の都道府県を取得
    unvisited_prefectures = Prefecture.objects.exclude(id__in=visited_prefectures).exclude(name="その他")
    
    if unvisited_prefectures.exists():
        return random.choice(unvisited_prefectures)
    return None

@login_required
def roulette_view(request):
    prefecture = get_random_unvisited_prefecture(request.user)
    if prefecture:
        return JsonResponse({'prefecture': prefecture.name})
    else:
        return JsonResponse({'error': '未訪問の都道府県がありません'})
    
@method_decorator([login_required, never_cache], name='dispatch')
class TravelDetailView(View):
    def get(self, request, travel_id):
        travel_record = get_object_or_404(TravelRecord, id=travel_id)
        
        fixed_categories = ['観光', '食べる', '宿泊']
        
        existing_categories = travel_record.category_set.values_list('category_name', flat=True)
        
        for category_name in fixed_categories:
            if category_name not in existing_categories:
                Category.objects.get_or_create(
                travel_record=travel_record,
                category_name=category_name
            )
            
        categories = travel_record.category_set.all()
        print("カテゴリ数:", categories.count())#デバッグ
        
        photos = []
        for category in categories:
            photos.extend(category.photo_set.all())
        
        return render(request, 'travel_detail.html', context={
            'travel_record': travel_record,
            'categories': categories,
            'photos': photos,
            'custom_categories_count': categories.exclude(category_name__in=fixed_categories).count(),
            'current_tab': '旅行概要',
        })
            
@method_decorator([login_required, never_cache], name='dispatch')
class TravelEditView(View):
    def get(self, request, travel_id):
        travel_record = get_object_or_404(TravelRecord, id=travel_id)
        form = TravelRecordForm(instance=travel_record)
        return render(request, 'travel_record_edit.html', context={
            'form':form,
            'travel_record': travel_record,
            'travel_id': travel_id
        })
        
    def post(self, request, travel_id):
        travel_record = get_object_or_404(TravelRecord, id=travel_id)
        form = TravelRecordForm(request.POST, request.FILES, instance=travel_record)
        if form.is_valid():
            form.save()
            return redirect('travel_detail', travel_id=travel_record.id)
        
        return render(request, 'travel_record_edit.html',context={
            'form':form,
            'travel_record': travel_record,
            'travel_id': travel_id
        })
        
@method_decorator([login_required, never_cache], name='dispatch')
class TravelDeleteView(View):
    def post(self, request, travel_id):
        travel_record = get_object_or_404(TravelRecord, id=travel_id)
        travel_record.delete()
        return redirect('travel_list')
    
@method_decorator([login_required, never_cache], name='dispatch')
class CategoryDetailView(View):
    def get(self, request, travel_id, category_id):
        travel_record = get_object_or_404(TravelRecord, id=travel_id)
        category = get_object_or_404(Category, id=category_id)
        
        photos = category.photo_set.all()
        categories = travel_record.category_set.all()
        
        current_tab = category.category_name
        
        active_tab = str(category_id) 
        
        return render(request, 'category_detail.html', context={
            'travel_record': travel_record,
            'category':category,
            'photos': photos,
            'categories': categories,
            'active_tab': active_tab,
            'current_tab': current_tab,#パンくずリスト
        })
        
@method_decorator(login_required, name='dispatch')
class CategoryAddView(View):
    def get(self, request, travel_id):
        travel_record = get_object_or_404(TravelRecord, id=travel_id)
        return render(request, 'add_category.html', {'travel_record':travel_record})
    
    def post(self, request, travel_id):
        travel_record = get_object_or_404(TravelRecord, id=travel_id)
        category_name = request.POST.get('category_name')
        current_category_count = travel_record.category_set.exclude(category_name__in=['観光', '食べる', '宿泊']).count()
        
        if current_category_count >= 2:
            error_message = "カテゴリは2つまでしか追加できません"
            return render(request, 'add_category.html', context={
                'travel_record': travel_record,
                'error_message': error_message,
            })
        
        if category_name:
            new_category = Category.objects.create(
                travel_record=travel_record,
                category_name=category_name,
                is_custom=True
                )
            return redirect('custom_category_detail', travel_id=travel_record.id, category_id=new_category.id)
        
        error_message = "カテゴリ名を入力してください"
        return render(request, 'add_category.html', context={
            'travel_record':travel_record,
            'error_message':error_message
        })


@method_decorator([login_required, never_cache], name='dispatch')
class CustomCategoryDetailView(View):
    def get(self, request, travel_id, category_id):
        travel_record = get_object_or_404(TravelRecord, id=travel_id)
        category = get_object_or_404(Category, id=category_id, travel_record=travel_record)
        
        photos = category.photo_set.all()
        categories = travel_record.category_set.all()

        current_tab = category.category_name
        active_tab = str(category_id)  # カスタムカテゴリ用

        return render(request, 'custom_category_detail.html', context={
            'travel_record': travel_record,
            'category': category,
            'photos': photos,
            'categories': categories,
            'active_tab': active_tab,
            'current_tab': current_tab,  # パンくずリスト
        })
    
@login_required
def travel_list(request):
    travel_records = TravelRecord.objects.filter(user=request.user)
    return render(request, 'travel_list.html',context= {
        'travel_records': travel_records
        })
    
@login_required
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        if request.POST.get('action') == 'delete':
            category.delete()  # カテゴリを削除
            return redirect('travel_detail', travel_id=category.travel_record.id)

        # カテゴリ名変更
        category_name = request.POST.get('category_name', '').strip()

        if category_name:
            category.category_name = category_name
            category.save()
            return redirect('custom_category_detail', travel_id=category.travel_record.id, category_id=category.id)

        error_message = "カテゴリ名を入力してください"
        return render(request, 'edit_category.html', context={
            'category': category,
            'error_message': error_message
        })

    return render(request, 'edit_category.html', {'category': category})      

@login_required
def add_photo(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    travel_record = category.travel_record
    
    if request.method == 'POST':
        print(request.FILES)
        form = PhotoForm(request.POST, request.FILES)
        
        photos = request.FILES.getlist('photo_url')#写真複数選択
        
        if not photos:
            return redirect('category_detail', travel_id=travel_record.id, category_id=category.id)
            
        for photo_file in photos:
            photo = Photo(photo_url=photo_file, category=category)
            photo.save()

        return redirect('category_detail', travel_id=travel_record.id, category_id=category.id)
            
    return render(request, 'add_photo.html',context={
        'form': form,
        'category': category
    })
    
@login_required
def delete_photo(request, travel_id, category_id, photo_id):
    photo = get_object_or_404(Photo, id=photo_id, category_id=category_id)
    
    if request.method == "POST":
        photo.delete()
        return redirect('category_detail',travel_id=travel_id, category_id=category_id)
    
    return redirect('category_detail',travel_id=travel_id, category_id=category_id)
        
@login_required
def edit_comment(request, travel_id, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        category_comment = request.POST.get('category_comment', '').strip()  # 空白を除去
        print(f"Received comment: '{category_comment}'")  # デバッグ用
        
        if category_comment:  # コメントが空でない場合のみ保存
            category.category_comment = category_comment
            category.save()
            print(f"Saved comment: '{category.category_comment}'")  # デバッグ用
            
            if category.is_custom:
                return redirect('custom_category_detail', travel_id=travel_id, category_id=category_id)
            else:
                return redirect('category_detail', travel_id=travel_id, category_id=category_id)

    return render(request, 'category_detail.html', context={
        'travel_record': get_object_or_404(TravelRecord, id=travel_id),
        'category': category,
        'photos': category.photo_set.all(),
        'categories': category.travel_record.category_set.all(),
        'active_tab': str(category_id),
        'current_tab': category.category_name,  # パンくずリスト
    })
    
@method_decorator([login_required, never_cache], name='dispatch')
class TravelMemoListView(View):
    def get(self, request, travel_record_id):
        travel_record = get_object_or_404(TravelRecord, id=travel_record_id)
        categories = Category.objects.filter(travel_record=travel_record)
        
        current_tab = 'たびメモ'#パンくずリスト
        active_tab = 'memo'
         
        memos = TravelMemo.objects.filter(travel_record_id=travel_record_id).order_by('created_at')
        form = TravelMemoForm()
        
        return render(request, 'travelmemo_list.html', context={
            'travel_record': travel_record,
            'memos': memos,
            'form': form,
            'categories': categories,
            'active_tab': active_tab, 
            'current_tab': current_tab,
        })
        
    def post(self, request, travel_record_id):
        travel_record = get_object_or_404(TravelRecord, id=travel_record_id)
        form = TravelMemoForm(request.POST, request.FILES)

        if form.is_valid():
            travel_memo = form.save(commit=False)
            travel_memo.travel_record = travel_record
            travel_memo.memo_location = form.cleaned_data.get('memo_location')
            travel_memo.latitude = form.cleaned_data.get('latitude')
            travel_memo.longitude = form.cleaned_data.get('longitude')
            
            if travel_memo.latitude is None or travel_memo.longitude is None:
                print("位置情報が提供されていません")
                travel_memo.memo_location = "位置情報未設定"
            else:       
            # Geopyを使って緯度・経度から住所を取得
                geolocator = Nominatim(user_agent="my_travelbook_app")
                try:
                    location = geolocator.reverse(f"{travel_memo.latitude}, {travel_memo.longitude}")
                    if location and location.raw.get('address'):
                        address = location.raw['address']
                        province = address.get('province', '')
                        city = address.get('city', address.get('town', address.get('village', '')))
                        travel_memo.memo_location = f"{province} {city}"
                except GeocoderServiceError as e:
                    travel_memo.memo_location = "住所情報が取得できませんでした"
                else:
                # 緯度・経度が無効な場合の処理
                    travel_memo.memo_location = "位置情報未設定"  # エラー時のデフォルト値
                    travel_memo.latitude = None
                    travel_memo.longitude = None
            
            # Base64の音声データをデコードしてaudio_pathに保存
            audio_data = form.cleaned_data.get('audio_data')
            if audio_data:
                try:
                    format, audio_str = audio_data.split(';base64,')
                    audio_file = ContentFile(base64.b64decode(audio_str), name='recording.mp3')
                    travel_memo.audio_path.save('recording.mp3', audio_file, save=False)
                except Exception as e:
                    print("音声データの保存に失敗しました: ", e)  # デバッグ用
            else:
                print("音声データが空です")  # デバッグ用
                
                print("Audio path:", travel_memo.audio_path)  # デバッグ用
            travel_memo.save()
            return redirect('travelmemo_list', travel_record_id=travel_record.id)
        
        memos = TravelMemo.objects.filter(travel_record=travel_record).order_by('created_at')
        return render(request, 'travelmemo_list.html', context={
            'travel_record': travel_record,
            'memos': memos,
            'form': form
            })

@login_required        
def delete_memo(request, memo_id):
    memo = get_object_or_404(TravelMemo, id=memo_id)
    travel_record_id = memo.travel_record.id
    memo.delete()
    return redirect('travelmemo_list', travel_record_id=travel_record_id)

@login_required  
def delete_all_memos(request, travel_record_id):
    travel_record = get_object_or_404(TravelRecord, id=travel_record_id)
    
    if request.method == 'POST':
        TravelMemo.objects.filter(travel_record=travel_record).delete()
        return redirect('travelmemo_list', travel_record_id=travel_record.id)

@login_required 
def search_travel_records(request):
    form = TravelSearchForm(request.GET or None)
    results = TravelRecord.objects.all()
    
    if form.is_valid():
        keyword = form.cleaned_data.get('keyword')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        
        if keyword:
            results = results.filter(
                Q(title__icontains=keyword) | 
                Q(prefecture__name__icontains=keyword) |
                Q(city__icontains=keyword)                
            )

        if date_from:
            results = results.filter(start_date__gte=date_from)
        if date_to:
            results = results.filter(end_date__lte=date_to)
            
    return render(request, 'search_results.html', context={
        'form': form,
        'results': results
        })