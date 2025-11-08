from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import CreateView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .models import User
import json

# Registration Flow Views
def register_select_role(request):
    """Step 1: Select account type for registration"""
    if request.user.is_authenticated:
        if request.user.is_game_admin:
            return redirect('authentication:admin_dashboard')
        else:
            return redirect('games:dashboard')
    
    if request.method == 'POST':
        role = request.POST.get('role')
        if role in ['user', 'admin']:
            request.session['register_role'] = role
            return redirect('authentication:register_form')
        else:
            messages.error(request, 'Please select a valid account type.')
    
    return render(request, 'authentication/register_select_role.html')

def register_form(request):
    """Step 2: Registration form with details"""
    if request.user.is_authenticated:
        if request.user.is_game_admin:
            return redirect('authentication:admin_dashboard')
        else:
            return redirect('games:dashboard')
    
    # Check if role was selected
    role = request.session.get('register_role')
    if not role:
        return redirect('authentication:register_select_role')
    
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        mobile_number = request.POST.get('mobile_number', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validation
        errors = []
        
        if not all([first_name, last_name, username, email, password, confirm_password]):
            errors.append('All fields are required.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        
        if User.objects.filter(username=username).exists():
            errors.append('Username already exists.')
        
        if User.objects.filter(email=email).exists():
            errors.append('Email already registered.')
        
        if mobile_number and len(mobile_number) < 10:
            errors.append('Please enter a valid mobile number.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            context = {
                'role': role,
                'form_data': request.POST
            }
            return render(request, 'authentication/register_form.html', context)
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                mobile_number=mobile_number,
                role=role
            )
            
            # Clear session data
            if 'register_role' in request.session:
                del request.session['register_role']
            
            # Store user data for success page
            request.session['registration_success'] = {
                'email': email,
                'role': role,
                'name': f"{first_name} {last_name}"
            }
            
            return redirect('authentication:register_success')
            
        except Exception as e:
            messages.error(request, 'Error creating account. Please try again.')
    
    context = {
        'role': role
    }
    return render(request, 'authentication/register_form.html', context)

def register_success(request):
    """Step 3: Registration successful"""
    success_data = request.session.get('registration_success')
    if not success_data:
        return redirect('authentication:register_select_role')
    
    # Clear success data from session
    del request.session['registration_success']
    
    context = {
        'success_data': success_data
    }
    return render(request, 'authentication/register_success.html', context)

# Login Flow Views
def login_select_role(request):
    """Step 1: Select login type"""
    if request.user.is_authenticated:
        if request.user.is_game_admin:
            return redirect('authentication:admin_dashboard')
        else:
            return redirect('games:dashboard')
    
    if request.method == 'POST':
        role = request.POST.get('role')
        if role in ['user', 'admin']:
            request.session['login_role'] = role
            return redirect('authentication:login_form')
        else:
            messages.error(request, 'Please select a valid login type.')
    
    return render(request, 'authentication/login_select_role.html')

def login_form(request):
    """Step 2: Login form"""
    if request.user.is_authenticated:
        if request.user.is_game_admin:
            return redirect('authentication:admin_dashboard')
        else:
            return redirect('games:dashboard')
    
    # Check if role was selected
    selected_role = request.session.get('login_role')
    if not selected_role:
        return redirect('authentication:login_select_role')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        
        if not email or not password:
            messages.error(request, 'Please enter both email and password.')
            context = {'selected_role': selected_role}
            return render(request, 'authentication/login_form.html', context)
        
        # Try to find user by email
        try:
            user_obj = User.objects.get(email=email)
            # Authenticate using username and password
            user = authenticate(request, username=user_obj.username, password=password)
            
            if user is not None:
                # Check if user role matches selected login type
                if (selected_role == 'admin' and not user.is_game_admin) or \
                   (selected_role == 'user' and user.is_game_admin):
                    messages.error(request, f'This account is not registered as a {selected_role}. Please select the correct login type.')
                    context = {'selected_role': selected_role}
                    return render(request, 'authentication/login_form.html', context)
                
                login(request, user)
                
                # Clear session data
                if 'login_role' in request.session:
                    del request.session['login_role']
                
                # Store success data
                request.session['login_success'] = {
                    'role': selected_role,
                    'name': user.first_name or user.username
                }
                
                return redirect('authentication:login_success')
            else:
                messages.error(request, 'Incorrect email or password.')
                
        except User.DoesNotExist:
            messages.error(request, 'Incorrect email or password.')
    
    context = {
        'selected_role': selected_role
    }
    return render(request, 'authentication/login_form.html', context)

def login_success(request):
    """Step 3: Login successful - redirect after showing success"""
    if not request.user.is_authenticated:
        return redirect('authentication:login_select_role')
    
    success_data = request.session.get('login_success')
    if success_data:
        del request.session['login_success']
        context = {'success_data': success_data}
        return render(request, 'authentication/login_success.html', context)
    
    # Direct redirect if no success data
    if request.user.is_game_admin:
        return redirect('authentication:admin_dashboard')
    else:
        return redirect('games:dashboard')

# Legacy views for backward compatibility
def login_view(request):
    """Legacy login view - redirect to new flow"""
    return redirect('authentication:login_select_role')

def register_view(request):
    """Legacy register view - redirect to new flow"""
    return redirect('authentication:register_select_role')

def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('authentication:login')

@login_required
def profile_view(request):
    """User profile view"""
    user = request.user
    
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.bio = request.POST.get('bio', '')
        
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']
        
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('authentication:profile')
    
    context = {
        'user': user,
        'recent_games': user.game_sessions.all()[:5]
    }
    return render(request, 'authentication/profile.html', context)

# API Views for REST Framework
@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    """API endpoint for user registration"""
    try:
        data = request.data
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not all([username, email, password]):
            return Response(
                {'error': 'Username, email, and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Username already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Email already registered'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Create token for the user
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'message': 'User created successfully',
            'user_id': user.id,
            'username': user.username,
            'token': token.key
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """API endpoint for user login"""
    try:
        data = request.data
        username = data.get('username')
        password = data.get('password')
        
        if not all([username, password]):
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username, password=password)
        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'message': 'Login successful',
                'user_id': user.id,
                'username': user.username,
                'token': token.key
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def api_logout(request):
    """API endpoint for user logout"""
    try:
        if hasattr(request.user, 'auth_token'):
            request.user.auth_token.delete()
        return Response(
            {'message': 'Logout successful'},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
