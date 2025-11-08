from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from datetime import timedelta
from .models import User, UserRole
from .decorators import admin_required
from games.models import GameSession, SudokuPuzzle, Achievement, ShapeGameAttempt


@admin_required
def admin_dashboard_view(request):
    """Admin-only dashboard with comprehensive user and system statistics"""
    
    # User Statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    blocked_users = User.objects.filter(is_active=False).count()
    admin_users = User.objects.filter(role=UserRole.ADMIN).count()
    regular_users = User.objects.filter(role=UserRole.USER).count()
    
    # Recent registrations (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_registrations = User.objects.filter(created_at__gte=thirty_days_ago).count()
    
    # Game Statistics
    total_puzzles = SudokuPuzzle.objects.count()
    active_puzzles = SudokuPuzzle.objects.filter(is_active=True).count()
    total_game_sessions = GameSession.objects.count()
    completed_games = GameSession.objects.filter(status='completed').count()
    
    # User Activity (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    active_this_week = User.objects.filter(last_login__gte=week_ago).count()
    
    # Recent Users (last 10 registered)
    recent_users = User.objects.order_by('-created_at')[:10]
    
    # Top Players by Score
    top_players = User.objects.filter(total_score__gt=0).order_by('-total_score')[:10]
    
    # System Health
    avg_completion_rate = GameSession.objects.filter(
        status='completed'
    ).count() / max(GameSession.objects.count(), 1) * 100
    
    context = {
        'page_title': 'Admin Dashboard',
        'stats': {
            'total_users': total_users,
            'active_users': active_users,
            'blocked_users': blocked_users,
            'admin_users': admin_users,
            'regular_users': regular_users,
            'recent_registrations': recent_registrations,
            'total_puzzles': total_puzzles,
            'active_puzzles': active_puzzles,
            'total_game_sessions': total_game_sessions,
            'completed_games': completed_games,
            'active_this_week': active_this_week,
            'avg_completion_rate': round(avg_completion_rate, 1),
        },
        'recent_users': recent_users,
        'top_players': top_players,
    }
    
    return render(request, 'authentication/admin/dashboard.html', context)


@admin_required
def user_management_view(request):
    """Admin view for managing all users"""
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    # Start with all users
    users = User.objects.all()
    
    # Apply search filter
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Apply role filter
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Apply status filter
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'blocked':
        users = users.filter(is_active=False)
    
    # Apply sorting
    users = users.order_by(sort_by)
    
    # Add statistics for each user
    users = users.annotate(
        total_games=Count('game_sessions'),
        completed_games=Count('game_sessions', filter=Q(game_sessions__status='completed')),
        shape_games=Count('shape_game_attempts')
    )
    
    # Pagination
    paginator = Paginator(users, 20)  # Show 20 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_title': 'User Management',
        'users': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'role_choices': UserRole.choices,
    }
    
    return render(request, 'authentication/admin/user_management.html', context)


@admin_required
def user_detail_view(request, user_id):
    """Detailed view of a specific user for admin management"""
    
    user = get_object_or_404(User, id=user_id)
    
    # User's game statistics
    total_games = user.game_sessions.count()
    completed_games = user.game_sessions.filter(status='completed').count()
    in_progress_games = user.game_sessions.filter(status='in_progress').count()
    
    # Shape game statistics
    shape_attempts = user.shape_game_attempts.count()
    completed_shape_games = user.shape_game_attempts.filter(status='completed').count()
    
    # Recent activity
    recent_games = user.game_sessions.order_by('-start_time')[:10]
    recent_shape_games = user.shape_game_attempts.order_by('-start_time')[:5]
    
    # Achievements
    achievements = user.achievements.all().order_by('-earned_at')
    
    # Account details
    days_since_joined = (timezone.now() - user.created_at).days
    last_activity = user.last_login
    
    context = {
        'page_title': f'User Details: {user.username}',
        'user_detail': user,
        'stats': {
            'total_games': total_games,
            'completed_games': completed_games,
            'in_progress_games': in_progress_games,
            'shape_attempts': shape_attempts,
            'completed_shape_games': completed_shape_games,
            'win_rate': round((completed_games / max(total_games, 1)) * 100, 1),
            'days_since_joined': days_since_joined,
        },
        'recent_games': recent_games,
        'recent_shape_games': recent_shape_games,
        'achievements': achievements,
        'last_activity': last_activity,
    }
    
    return render(request, 'authentication/admin/user_detail.html', context)


@admin_required
def edit_user_view(request, user_id):
    """Admin view to edit user details"""
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Update user details
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.role = request.POST.get('role', UserRole.USER)
        user.bio = request.POST.get('bio', '')
        
        # Handle active status
        user.is_active = request.POST.get('is_active') == 'on'
        
        # Handle staff status (only for admins)
        if request.POST.get('is_staff') == 'on':
            user.is_staff = True
        else:
            user.is_staff = False
        
        try:
            user.save()
            messages.success(request, f'User {user.username} updated successfully!')
            return redirect('authentication:user_detail', user_id=user.id)
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    context = {
        'page_title': f'Edit User: {user.username}',
        'user_detail': user,
        'role_choices': UserRole.choices,
    }
    
    return render(request, 'authentication/admin/edit_user.html', context)


@admin_required
def toggle_user_status(request, user_id):
    """AJAX endpoint to block/unblock users"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    user = get_object_or_404(User, id=user_id)
    
    # Prevent admin from blocking themselves
    if user == request.user:
        return JsonResponse({'success': False, 'error': 'Cannot block yourself'})
    
    # Prevent blocking other admins (optional security measure)
    if user.role == UserRole.ADMIN and user != request.user:
        return JsonResponse({'success': False, 'error': 'Cannot block other administrators'})
    
    # Toggle user status
    user.is_active = not user.is_active
    user.save()
    
    action = 'unblocked' if user.is_active else 'blocked'
    
    return JsonResponse({
        'success': True,
        'action': action,
        'user_id': user.id,
        'is_active': user.is_active,
        'message': f'User {user.username} has been {action}'
    })


@admin_required
def delete_user_view(request, user_id):
    """Admin view to delete a user (with confirmation)"""
    
    user = get_object_or_404(User, id=user_id)
    
    # Prevent admin from deleting themselves
    if user == request.user:
        messages.error(request, 'Cannot delete your own account')
        return redirect('authentication:user_management')
    
    # Prevent deleting other admins
    if user.role == UserRole.ADMIN:
        messages.error(request, 'Cannot delete administrator accounts')
        return redirect('authentication:user_management')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User {username} has been deleted successfully')
        return redirect('authentication:user_management')
    
    context = {
        'page_title': f'Delete User: {user.username}',
        'user_detail': user,
    }
    
    return render(request, 'authentication/admin/delete_user.html', context)


@admin_required
def bulk_user_actions(request):
    """Handle bulk actions on multiple users"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    action = request.POST.get('action')
    user_ids = request.POST.getlist('user_ids')
    
    if not user_ids:
        return JsonResponse({'success': False, 'error': 'No users selected'})
    
    # Get users (excluding current admin)
    users = User.objects.filter(id__in=user_ids).exclude(id=request.user.id)
    
    success_count = 0
    
    if action == 'block':
        users.update(is_active=False)
        success_count = users.count()
        message = f'{success_count} users have been blocked'
        
    elif action == 'unblock':
        users.update(is_active=True)
        success_count = users.count()
        message = f'{success_count} users have been unblocked'
        
    elif action == 'delete':
        # Only delete regular users, not admins
        regular_users = users.filter(role=UserRole.USER)
        success_count = regular_users.count()
        regular_users.delete()
        message = f'{success_count} users have been deleted'
        
    else:
        return JsonResponse({'success': False, 'error': 'Invalid action'})
    
    return JsonResponse({
        'success': True,
        'message': message,
        'affected_count': success_count
    })


@admin_required
def user_statistics_view(request):
    """Detailed user statistics and analytics for admins"""
    
    # Registration trends (last 12 months)
    from django.db.models import Count
    from django.db.models.functions import TruncMonth
    
    registration_trends = User.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=365)
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Activity statistics
    active_users_today = User.objects.filter(
        last_login__gte=timezone.now() - timedelta(days=1)
    ).count()
    
    active_users_week = User.objects.filter(
        last_login__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    active_users_month = User.objects.filter(
        last_login__gte=timezone.now() - timedelta(days=30)
    ).count()
    
    # Top performing users
    top_scorers = User.objects.filter(total_score__gt=0).order_by('-total_score')[:20]
    most_active = User.objects.filter(games_played__gt=0).order_by('-games_played')[:20]
    
    context = {
        'page_title': 'User Statistics',
        'registration_trends': list(registration_trends),
        'activity_stats': {
            'today': active_users_today,
            'week': active_users_week,
            'month': active_users_month,
        },
        'top_scorers': top_scorers,
        'most_active': most_active,
    }
    
    return render(request, 'authentication/admin/user_statistics.html', context)