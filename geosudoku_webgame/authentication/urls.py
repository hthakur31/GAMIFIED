from django.urls import path
from . import views, admin_views

app_name = 'authentication'

urlpatterns = [
    # New step-by-step authentication flow
    path('register/', views.register_select_role, name='register'),
    path('register/select-role/', views.register_select_role, name='register_select_role'),
    path('register/form/', views.register_form, name='register_form'),
    path('register/success/', views.register_success, name='register_success'),
    
    path('login/', views.login_select_role, name='login'),
    path('login/select-role/', views.login_select_role, name='login_select_role'),
    path('login/form/', views.login_form, name='login_form'),
    path('login/success/', views.login_success, name='login_success'),
    
    # Legacy URLs for backward compatibility
    path('login-old/', views.login_view, name='login_old'),
    path('register-old/', views.register_view, name='register_old'),
    
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    
    # Admin user management URLs
    path('admin/dashboard/', admin_views.admin_dashboard_view, name='admin_dashboard'),
    path('admin/users/', admin_views.user_management_view, name='user_management'),
    path('admin/users/<int:user_id>/', admin_views.user_detail_view, name='user_detail'),
    path('admin/users/<int:user_id>/edit/', admin_views.edit_user_view, name='edit_user'),
    path('admin/users/<int:user_id>/toggle-status/', admin_views.toggle_user_status, name='toggle_user_status'),
    path('admin/users/<int:user_id>/delete/', admin_views.delete_user_view, name='delete_user'),
    path('admin/users/bulk-actions/', admin_views.bulk_user_actions, name='bulk_user_actions'),
    path('admin/statistics/', admin_views.user_statistics_view, name='user_statistics'),
    
    # API endpoints
    path('api/register/', views.api_register, name='api_register'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/logout/', views.api_logout, name='api_logout'),
]