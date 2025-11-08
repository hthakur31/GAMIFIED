from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.http import JsonResponse
from django.utils import timezone
from .models import (
    PuzzleLevel, LevelPuzzle, UserLevelProgress, ShapeGame, 
    Achievement, UserAchievement, Shape, GridTemplate
)
from authentication.decorators import admin_required
from authentication.models import User
import json


@admin_required
def level_management_view(request):
    """Admin view for managing puzzle levels"""
    
    levels = PuzzleLevel.objects.all().annotate(
        total_puzzles=Count('level_puzzles'),
        active_puzzles=Count('level_puzzles', filter=Q(level_puzzles__is_active=True)),
        users_started=Count('user_progress', distinct=True),
        users_completed=Count('user_progress', filter=Q(user_progress__is_completed=True), distinct=True)
    ).order_by('level_number')
    
    context = {
        'page_title': 'Level Management',
        'levels': levels,
    }
    
    return render(request, 'games/admin/level_management.html', context)


@admin_required
def create_level_view(request):
    """Create a new puzzle level"""
    
    if request.method == 'POST':
        level_number = request.POST.get('level_number')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        puzzles_required = request.POST.get('puzzles_required', 10)
        unlock_level = request.POST.get('unlock_level', 0)
        
        try:
            level = PuzzleLevel.objects.create(
                level_number=int(level_number),
                name=name,
                description=description,
                puzzles_required=int(puzzles_required),
                unlock_level=int(unlock_level),
                created_by=request.user
            )
            messages.success(request, f'Level {level.level_number}: {level.name} created successfully!')
            return redirect('games:level_management')
        except ValueError as e:
            messages.error(request, f'Invalid data provided: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error creating level: {str(e)}')
    
    # Get next level number
    last_level = PuzzleLevel.objects.last()
    next_level_number = 1 if not last_level else last_level.level_number + 1
    
    context = {
        'page_title': 'Create Level',
        'next_level_number': next_level_number,
    }
    
    return render(request, 'games/admin/create_level.html', context)


@admin_required
def edit_level_view(request, level_id):
    """Edit an existing puzzle level"""
    
    level = get_object_or_404(PuzzleLevel, id=level_id)
    
    if request.method == 'POST':
        level.name = request.POST.get('name')
        level.description = request.POST.get('description', '')
        level.puzzles_required = int(request.POST.get('puzzles_required', 10))
        level.unlock_level = int(request.POST.get('unlock_level', 0))
        level.is_active = request.POST.get('is_active') == 'on'
        
        try:
            level.save()
            messages.success(request, f'Level {level.level_number}: {level.name} updated successfully!')
            return redirect('games:level_management')
        except Exception as e:
            messages.error(request, f'Error updating level: {str(e)}')
    
    context = {
        'page_title': f'Edit Level {level.level_number}',
        'level': level,
    }
    
    return render(request, 'games/admin/edit_level.html', context)


@admin_required
def level_detail_view(request, level_id):
    """Detailed view of a specific level with puzzle assignments"""
    
    level = get_object_or_404(PuzzleLevel, id=level_id)
    
    # Get assigned puzzles
    level_puzzles = LevelPuzzle.objects.filter(level=level).select_related('shape_game').order_by('order_in_level')
    
    # Get available puzzles not yet assigned to this level
    assigned_game_ids = level_puzzles.values_list('shape_game_id', flat=True)
    available_games = ShapeGame.objects.filter(is_active=True).exclude(id__in=assigned_game_ids)
    
    # Get user progress for this level
    user_progress = UserLevelProgress.objects.filter(level=level).select_related('user').order_by('-total_score')
    
    context = {
        'page_title': f'Level {level.level_number}: {level.name}',
        'level': level,
        'level_puzzles': level_puzzles,
        'available_games': available_games,
        'user_progress': user_progress,
    }
    
    return render(request, 'games/admin/level_detail.html', context)


@admin_required
def assign_puzzle_to_level(request, level_id):
    """Assign a puzzle to a level"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    level = get_object_or_404(PuzzleLevel, id=level_id)
    shape_game_id = request.POST.get('shape_game_id')
    points_reward = request.POST.get('points_reward', 100)
    
    try:
        shape_game = ShapeGame.objects.get(id=shape_game_id)
        
        # Get next order number
        last_order = LevelPuzzle.objects.filter(level=level).aggregate(
            max_order=Count('order_in_level')
        )['max_order'] or 0
        
        level_puzzle = LevelPuzzle.objects.create(
            level=level,
            shape_game=shape_game,
            order_in_level=last_order + 1,
            points_reward=int(points_reward)
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Puzzle "{shape_game.name}" assigned to level {level.level_number}'
        })
        
    except ShapeGame.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Puzzle not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def remove_puzzle_from_level(request, level_id, puzzle_id):
    """Remove a puzzle from a level"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    level = get_object_or_404(PuzzleLevel, id=level_id)
    level_puzzle = get_object_or_404(LevelPuzzle, id=puzzle_id, level=level)
    
    try:
        puzzle_name = level_puzzle.shape_game.name
        level_puzzle.delete()
        
        # Reorder remaining puzzles
        remaining_puzzles = LevelPuzzle.objects.filter(level=level).order_by('order_in_level')
        for i, puzzle in enumerate(remaining_puzzles, 1):
            puzzle.order_in_level = i
            puzzle.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Puzzle "{puzzle_name}" removed from level {level.level_number}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def user_level_progress_view(request):
    """View user progress across all levels"""
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    level_filter = request.GET.get('level', '')
    status_filter = request.GET.get('status', '')
    
    # Base queryset
    progress_records = UserLevelProgress.objects.select_related('user', 'level').all()
    
    # Apply filters
    if search_query:
        progress_records = progress_records.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    if level_filter:
        progress_records = progress_records.filter(level__level_number=level_filter)
    
    if status_filter == 'completed':
        progress_records = progress_records.filter(is_completed=True)
    elif status_filter == 'in_progress':
        progress_records = progress_records.filter(is_completed=False, puzzles_completed__gt=0)
    elif status_filter == 'not_started':
        progress_records = progress_records.filter(puzzles_completed=0)
    
    # Pagination
    paginator = Paginator(progress_records, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get levels for filter
    levels = PuzzleLevel.objects.filter(is_active=True).order_by('level_number')
    
    context = {
        'page_title': 'User Level Progress',
        'progress_records': page_obj,
        'levels': levels,
        'search_query': search_query,
        'level_filter': level_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'games/admin/user_level_progress.html', context)


@admin_required
def reset_user_progress(request, user_id, level_id):
    """Reset a user's progress for a specific level"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    user = get_object_or_404(User, id=user_id)
    level = get_object_or_404(PuzzleLevel, id=level_id)
    
    try:
        progress = UserLevelProgress.objects.get(user=user, level=level)
        progress.puzzles_completed = 0
        progress.is_completed = False
        progress.completed_at = None
        progress.total_score = 0
        progress.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Progress reset for {user.username} on level {level.level_number}'
        })
        
    except UserLevelProgress.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Progress record not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def achievement_management_view(request):
    """Manage system achievements"""
    
    achievements = Achievement.objects.all().annotate(
        users_earned=Count('earned_by', distinct=True)
    ).order_by('requirement_type', 'requirement_value')
    
    context = {
        'page_title': 'Achievement Management',
        'achievements': achievements,
    }
    
    return render(request, 'games/admin/achievement_management.html', context)


@admin_required
def create_achievement_view(request):
    """Create a new achievement"""
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        icon = request.POST.get('icon', 'trophy')
        points_reward = request.POST.get('points_reward', 50)
        requirement_type = request.POST.get('requirement_type')
        requirement_value = request.POST.get('requirement_value')
        
        try:
            achievement = Achievement.objects.create(
                name=name,
                description=description,
                icon=icon,
                points_reward=int(points_reward),
                requirement_type=requirement_type,
                requirement_value=int(requirement_value)
            )
            messages.success(request, f'Achievement "{achievement.name}" created successfully!')
            return redirect('games:achievement_management')
        except Exception as e:
            messages.error(request, f'Error creating achievement: {str(e)}')
    
    context = {
        'page_title': 'Create Achievement',
        'requirement_types': Achievement._meta.get_field('requirement_type').choices,
    }
    
    return render(request, 'games/admin/create_achievement.html', context)


@admin_required
def user_game_stats_view(request):
    """Comprehensive user gaming statistics"""
    
    # Overall statistics
    total_users = User.objects.count()
    active_players = User.objects.filter(shape_game_attempts__isnull=False).distinct().count()
    total_levels = PuzzleLevel.objects.filter(is_active=True).count()
    total_achievements = Achievement.objects.filter(is_active=True).count()
    
    # Level completion statistics
    level_stats = PuzzleLevel.objects.filter(is_active=True).annotate(
        users_started=Count('user_progress', distinct=True),
        users_completed=Count('user_progress', filter=Q(user_progress__is_completed=True), distinct=True)
    ).order_by('level_number')
    
    # Top performers
    top_scorers = User.objects.filter(total_score__gt=0).order_by('-total_score')[:10]
    
    # Recent achievements
    recent_achievements = UserAchievement.objects.select_related(
        'user', 'achievement'
    ).order_by('-earned_at')[:20]
    
    context = {
        'page_title': 'User Game Statistics',
        'stats': {
            'total_users': total_users,
            'active_players': active_players,
            'total_levels': total_levels,
            'total_achievements': total_achievements,
        },
        'level_stats': level_stats,
        'top_scorers': top_scorers,
        'recent_achievements': recent_achievements,
    }
    
    return render(request, 'games/admin/user_game_stats.html', context)


@admin_required
def bulk_level_operations(request):
    """Handle bulk operations on levels"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    action = request.POST.get('action')
    level_ids = request.POST.getlist('level_ids')
    
    if not level_ids:
        return JsonResponse({'success': False, 'error': 'No levels selected'})
    
    levels = PuzzleLevel.objects.filter(id__in=level_ids)
    success_count = 0
    
    try:
        if action == 'activate':
            levels.update(is_active=True)
            success_count = levels.count()
            message = f'{success_count} levels have been activated'
            
        elif action == 'deactivate':
            levels.update(is_active=False)
            success_count = levels.count()
            message = f'{success_count} levels have been deactivated'
            
        elif action == 'delete':
            success_count = levels.count()
            levels.delete()
            message = f'{success_count} levels have been deleted'
            
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'})
        
        return JsonResponse({
            'success': True,
            'message': message,
            'affected_count': success_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})