"""
Custom decorators for role-based access control
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


def admin_required(view_func):
    """
    Decorator to require admin role for accessing a view
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_game_admin:
            messages.error(request, 'You need admin privileges to access this page.')
            return redirect('games:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def role_required(allowed_roles):
    """
    Decorator to require specific roles for accessing a view
    
    Args:
        allowed_roles: List of roles or single role string ('admin', 'user')
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]
    
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user_role = getattr(request.user, 'role', 'user')
            
            if user_role not in allowed_roles and not request.user.is_superuser:
                messages.error(request, f'Access denied. Required role: {", ".join(allowed_roles)}')
                return redirect('games:dashboard')
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def user_can_access_admin_features(user):
    """
    Check if user can access admin features
    """
    return user.is_authenticated and (
        user.is_superuser or 
        user.is_staff or 
        getattr(user, 'is_game_admin', False)
    )


def user_can_manage_shapes(user):
    """
    Check if user can manage shapes
    """
    return user_can_access_admin_features(user)


def user_can_create_games(user):
    """
    Check if user can create games
    """
    return user_can_access_admin_features(user)


class RoleRequiredMixin:
    """
    Mixin for class-based views to require specific roles
    """
    required_roles = None
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('authentication:login')
            
        if self.required_roles:
            user_role = getattr(request.user, 'role', 'user')
            
            if user_role not in self.required_roles and not request.user.is_superuser:
                messages.error(request, f'Access denied. Required role: {", ".join(self.required_roles)}')
                return redirect('games:dashboard')
                
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(RoleRequiredMixin):
    """
    Mixin for class-based views that require admin access
    """
    required_roles = ['admin']
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('authentication:login')
            
        if not request.user.is_game_admin:
            messages.error(request, 'You need admin privileges to access this page.')
            return redirect('games:dashboard')
            
        return super(RoleRequiredMixin, self).dispatch(request, *args, **kwargs)