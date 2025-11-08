from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q, Avg, Count, Max
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import (
    SudokuPuzzle, GameSession, Leaderboard, Achievement, GameStatus,
    Shape, GridTemplate, ShapeGame, ShapeGameAttempt, PuzzleLevel, LevelPuzzle
)
from .forms import ShapeUploadForm, GridTemplateForm, ShapeGameForm, GridTemplateBuilderForm
import os
from authentication.decorators import admin_required, role_required, user_can_access_admin_features
from authentication.models import User
import json

def home_view(request):
    """Home page view"""
    if request.user.is_authenticated:
        return redirect('games:dashboard')
    return render(request, 'games/home.html')

@login_required
def dashboard_view(request):
    """Enhanced user dashboard with role-specific features and level progression"""
    user = request.user
    
    # Redirect admin users to their specific admin dashboard
    if user.is_game_admin:
        return redirect('authentication:admin_dashboard')
    
    # User-specific level progression data
    from .models import PuzzleLevel, UserLevelProgress, LevelPuzzle, UserPuzzleAttempt
    
    # Get user's current level and progress
    user_progress = UserLevelProgress.objects.filter(user=user).select_related('level').order_by('level__level_number')
    current_level = None
    unlocked_levels = []
    
    for progress in user_progress:
        if progress.level.is_unlocked_for_user(user):
            unlocked_levels.append(progress)
            if not progress.is_completed:
                current_level = progress
                break
    
    # If no current level, find the next unlocked level
    if not current_level:
        all_levels = PuzzleLevel.objects.filter(is_active=True).order_by('level_number')
        for level in all_levels:
            if level.is_unlocked_for_user(user):
                progress, created = UserLevelProgress.objects.get_or_create(
                    user=user,
                    level=level,
                    defaults={'puzzles_completed': 0, 'is_completed': False}
                )
                if not progress.is_completed:
                    current_level = progress
                    break
    
    # Recent game activity (shape games only for users)
    recent_shape_games = ShapeGameAttempt.objects.filter(user=user).order_by('-start_time')[:5]
    
    # User statistics
    total_shape_games = ShapeGameAttempt.objects.filter(user=user).count()
    completed_shape_games = ShapeGameAttempt.objects.filter(user=user, status='completed').count()
    shape_win_rate = (completed_shape_games / total_shape_games * 100) if total_shape_games > 0 else 0
    
    # Performance metrics
    avg_completion_time = ShapeGameAttempt.objects.filter(
        user=user, 
        status='completed',
        time_taken_seconds__isnull=False
    ).aggregate(avg_time=Avg('time_taken_seconds'))['avg_time']
    
    best_score = ShapeGameAttempt.objects.filter(user=user).aggregate(
        best=Max('score')
    )['best'] or 0
    
    # Level completion statistics
    completed_levels = user_progress.filter(is_completed=True).count()
    total_levels_unlocked = len(unlocked_levels)
    
    # Time-based performance (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_performance = ShapeGameAttempt.objects.filter(
        user=user,
        start_time__gte=thirty_days_ago
    ).aggregate(
        games_this_month=Count('id'),
        avg_score=Avg('score'),
        completion_rate=Count('id', filter=Q(status='completed')) * 100.0 / Count('id')
    )
    
    # Available puzzles in current level
    available_puzzles = []
    if current_level:
        level_puzzles = LevelPuzzle.objects.filter(
            level=current_level.level, 
            is_active=True
        ).select_related('shape_game')[:6]  # Show first 6 puzzles
        
        for level_puzzle in level_puzzles:
            # Check if user has attempted this puzzle
            attempt = UserPuzzleAttempt.objects.filter(
                user=user,
                level_puzzle=level_puzzle
            ).first()
            
            available_puzzles.append({
                'level_puzzle': level_puzzle,
                'attempted': attempt is not None,
                'completed': attempt.is_completed if attempt else False,
                'score': attempt.score_earned if attempt else 0
            })
    
    # User achievements
    user_achievements = user.user_achievements.select_related('achievement').order_by('-earned_at')[:5]
    
    # Quick actions for regular users (no admin functions)
    quick_actions = [
        {'name': 'Continue Level', 'url': 'games:level_play', 'url_params': {'level_id': current_level.level.id} if current_level else None, 'icon': 'fas fa-play', 'color': 'primary'},
        {'name': 'View Levels', 'url': 'games:level_list', 'icon': 'fas fa-layer-group', 'color': 'info', 'badge': 'NEW', 'badge_color': 'success'},
        {'name': 'Leaderboard', 'url': 'games:leaderboard', 'icon': 'fas fa-trophy', 'color': 'warning'},
        {'name': 'My Profile', 'url': 'authentication:profile', 'icon': 'fas fa-user', 'color': 'secondary'},
    ]
    
    context = {
        'current_level': current_level,
        'unlocked_levels': unlocked_levels[:5],  # Show recent 5 unlocked levels
        'available_puzzles': available_puzzles,
        'recent_shape_games': recent_shape_games,
        'achievements': user_achievements,
        'stats': {
            'total_games': total_shape_games,
            'completed_games': completed_shape_games,
            'win_rate': round(shape_win_rate, 1),
            'total_score': user.total_score,
            'best_score': best_score,
            'avg_completion_time': round(avg_completion_time / 60, 1) if avg_completion_time else None,
            'completed_levels': completed_levels,
            'total_levels_unlocked': total_levels_unlocked,
            'current_level_progress': round(current_level.completion_percentage, 1) if current_level else 0,
        },
        'recent_performance': recent_performance,
        'quick_actions': quick_actions,
        'is_admin': False,  # Users should not see admin features
    }
    return render(request, 'games/user_dashboard.html', context)

@login_required
def puzzle_list_view(request):
    """List all available puzzles"""
    difficulty = request.GET.get('difficulty', '')
    puzzles = SudokuPuzzle.objects.filter(is_active=True)
    
    if difficulty:
        puzzles = puzzles.filter(difficulty=difficulty)
    
    context = {
        'puzzles': puzzles,
        'selected_difficulty': difficulty
    }
    return render(request, 'games/puzzle_list.html', context)

@login_required
def play_puzzle_view(request, puzzle_id):
    """Play a specific puzzle"""
    puzzle = get_object_or_404(SudokuPuzzle, id=puzzle_id, is_active=True)
    
    # Get or create game session
    game_session, created = GameSession.objects.get_or_create(
        user=request.user,
        puzzle=puzzle,
        defaults={'current_state': puzzle.puzzle_data}
    )
    
    context = {
        'puzzle': puzzle,
        'game_session': game_session,
        'puzzle_data': json.dumps(puzzle.puzzle_data),
        'regions_data': json.dumps(puzzle.regions_data),
        'current_state': json.dumps(game_session.current_state)
    }
    return render(request, 'games/play_puzzle.html', context)

@admin_required
def create_puzzle_view(request):
    """Create a new puzzle - Admin only"""
    if request.method == 'POST':
        difficulty = request.POST.get('difficulty', 'easy')
        
        # Generate a new puzzle
        puzzle_data, solution_data, regions_data = SudokuPuzzle.generate_basic_puzzle(difficulty)
        
        puzzle = SudokuPuzzle.objects.create(
            difficulty=difficulty,
            puzzle_data=puzzle_data,
            solution_data=solution_data,
            regions_data=regions_data,
            created_by=request.user
        )
        
        messages.success(request, 'Puzzle created successfully!')
        return redirect('games:play_puzzle', puzzle_id=puzzle.id)
    
    return render(request, 'games/create_puzzle.html')

def leaderboard_view(request):
    """Leaderboard view"""
    difficulty = request.GET.get('difficulty', 'easy')
    
    leaderboard_entries = Leaderboard.objects.filter(
        difficulty=difficulty
    ).select_related('user')[:10]
    
    context = {
        'leaderboard_entries': leaderboard_entries,
        'selected_difficulty': difficulty
    }
    return render(request, 'games/leaderboard.html', context)

# API Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_puzzle_list(request):
    """API endpoint to get list of puzzles"""
    try:
        difficulty = request.GET.get('difficulty', '')
        puzzles = SudokuPuzzle.objects.filter(is_active=True)
        
        if difficulty:
            puzzles = puzzles.filter(difficulty=difficulty)
        
        puzzle_data = []
        for puzzle in puzzles:
            puzzle_data.append({
                'id': puzzle.id,
                'difficulty': puzzle.difficulty,
                'created_at': puzzle.created_at.isoformat(),
                'has_active_session': GameSession.objects.filter(
                    user=request.user, 
                    puzzle=puzzle, 
                    status=GameStatus.IN_PROGRESS
                ).exists()
            })
        
        return Response({
            'puzzles': puzzle_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_game_session(request, puzzle_id):
    """API endpoint for game session operations"""
    try:
        puzzle = get_object_or_404(SudokuPuzzle, id=puzzle_id, is_active=True)
        
        if request.method == 'GET':
            try:
                game_session = GameSession.objects.get(user=request.user, puzzle=puzzle)
                return Response({
                    'session_id': game_session.id,
                    'current_state': game_session.current_state,
                    'status': game_session.status,
                    'score': game_session.score,
                    'hints_used': game_session.hints_used,
                    'mistakes_made': game_session.mistakes_made,
                    'start_time': game_session.start_time.isoformat(),
                    'puzzle_data': puzzle.puzzle_data,
                    'regions_data': puzzle.regions_data
                }, status=status.HTTP_200_OK)
            except GameSession.DoesNotExist:
                return Response({
                    'error': 'No active game session found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        elif request.method == 'POST':
            # Create or update game session
            game_session, created = GameSession.objects.get_or_create(
                user=request.user,
                puzzle=puzzle,
                defaults={'current_state': puzzle.puzzle_data}
            )
            
            return Response({
                'session_id': game_session.id,
                'created': created,
                'current_state': game_session.current_state,
                'puzzle_data': puzzle.puzzle_data,
                'regions_data': puzzle.regions_data
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
            
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_save_game_state(request, session_id):
    """API endpoint to save game state"""
    try:
        game_session = get_object_or_404(GameSession, id=session_id, user=request.user)
        
        data = request.data
        new_state = data.get('current_state')
        is_completed = data.get('is_completed', False)
        
        if new_state:
            game_session.current_state = new_state
        
        if is_completed:
            game_session.status = GameStatus.COMPLETED
            game_session.end_time = timezone.now()
            game_session.score = game_session.calculate_score()
            
            # Update user statistics
            user = game_session.user
            user.total_score += game_session.score
            user.games_played += 1
            user.games_won += 1
            user.save()
            
            # Check for achievements
            check_achievements(user, game_session)
        
        game_session.save()
        
        return Response({
            'message': 'Game state saved successfully',
            'score': game_session.score,
            'status': game_session.status
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_validate_move(request):
    """API endpoint to validate a sudoku move"""
    try:
        data = request.data
        board = data.get('board')
        row = data.get('row')
        col = data.get('col')
        value = data.get('value')
        
        is_valid = validate_sudoku_move(board, row, col, value)
        
        return Response({
            'is_valid': is_valid
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def validate_sudoku_move(board, row, col, value):
    """Validate if a move is legal in Sudoku"""
    if not (0 <= row < 9 and 0 <= col < 9 and 1 <= value <= 9):
        return False
    
    # Check row
    for c in range(9):
        if c != col and board[row][c] == value:
            return False
    
    # Check column
    for r in range(9):
        if r != row and board[r][col] == value:
            return False
    
    # Check 3x3 box
    box_row, box_col = 3 * (row // 3), 3 * (col // 3)
    for r in range(box_row, box_row + 3):
        for c in range(box_col, box_col + 3):
            if (r != row or c != col) and board[r][c] == value:
                return False
    
    return True

def check_achievements(user, game_session):
    """Check and award achievements"""
    # First win achievement
    if user.games_won == 1:
        Achievement.objects.get_or_create(
            user=user,
            achievement_type='first_win',
            defaults={
                'name': 'First Victory',
                'description': 'Complete your first GeoSudoku puzzle',
                'icon': '🎉'
            }
        )
    
    # Speed demon (complete in under 10 minutes)
    if game_session.duration and game_session.duration.seconds < 600:
        Achievement.objects.get_or_create(
            user=user,
            achievement_type='speed_demon',
            defaults={
                'name': 'Speed Demon',
                'description': 'Complete a puzzle in under 10 minutes',
                'icon': '⚡'
            }
        )
    
    # Perfectionist (no mistakes or hints)
    if game_session.mistakes_made == 0 and game_session.hints_used == 0:
        Achievement.objects.get_or_create(
            user=user,
            achievement_type='perfectionist',
            defaults={
                'name': 'Perfectionist',
                'description': 'Complete a puzzle without mistakes or hints',
                'icon': '💎'
            }
        )

# Helper function to check if user is game admin
def is_game_admin(user):
    """Check if user has game admin permissions"""
    return user.is_authenticated and (user.is_superuser or getattr(user, 'is_game_admin', False))

# Shape Management Views

@admin_required
def shape_management_view(request):
    """Admin view for managing shapes"""
    shapes = Shape.objects.all().order_by('-created_at')
    context = {
        'shapes': shapes,
        'page_title': 'Shape Management'
    }
    return render(request, 'games/admin/shape_management.html', context)

@user_passes_test(is_game_admin)
def shape_upload_view(request):
    """Admin view for uploading new shapes"""
    if request.method == 'POST':
        form = ShapeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            shape = form.save(commit=False)
            shape.created_by = request.user
            shape.save()
            messages.success(request, f'Shape "{shape.name}" uploaded successfully!')
            return redirect('games:manage_shapes')
    else:
        form = ShapeUploadForm()
    
    context = {
        'form': form,
        'page_title': 'Upload Shape'
    }
    return render(request, 'games/admin/shape_upload.html', context)

@user_passes_test(is_game_admin)
def shape_edit_view(request, shape_id):
    """Admin view for editing shapes"""
    shape = get_object_or_404(Shape, id=shape_id)
    
    if request.method == 'POST':
        form = ShapeUploadForm(request.POST, request.FILES, instance=shape)
        if form.is_valid():
            form.save()
            messages.success(request, f'Shape "{shape.name}" updated successfully!')
            return redirect('games:manage_shapes')
    else:
        form = ShapeUploadForm(instance=shape)
    
    context = {
        'form': form,
        'shape': shape,
        'page_title': f'Edit Shape: {shape.name}'
    }
    return render(request, 'games/admin/shape_upload.html', context)

@user_passes_test(is_game_admin)
def shape_delete_view(request, shape_id):
    """Admin view for deleting shapes"""
    shape = get_object_or_404(Shape, id=shape_id)
    
    if request.method == 'POST':
        shape_name = shape.name
        shape.delete()
        messages.success(request, f'Shape "{shape_name}" deleted successfully!')
        return redirect('games:manage_shapes')
    
    context = {
        'shape': shape,
        'page_title': f'Delete Shape: {shape.name}'
    }
    return render(request, 'games/admin/shape_delete.html', context)

# Grid Template Management Views

@user_passes_test(is_game_admin)
def template_management_view(request):
    """Admin view for managing grid templates"""
    templates = GridTemplate.objects.all().order_by('-created_at')
    context = {
        'templates': templates,
        'page_title': 'Grid Template Management'
    }
    return render(request, 'games/admin/template_management.html', context)

@user_passes_test(is_game_admin)
def template_create_view(request):
    """Admin view for creating grid templates"""
    if request.method == 'POST':
        form = GridTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            messages.success(request, f'Template "{template.name}" created successfully!')
            return redirect('games:manage_templates')
    else:
        form = GridTemplateForm()
    
    context = {
        'form': form,
        'page_title': 'Create Grid Template'
    }
    return render(request, 'games/admin/template_create.html', context)

@user_passes_test(is_game_admin)
def template_builder_view(request):
    """Visual grid template builder"""
    if request.method == 'POST':
        form = GridTemplateBuilderForm(request.POST)
        if form.is_valid():
            # Parse the complex grid data
            grid_data_json = form.cleaned_data['grid_data']
            grid_data_parsed = json.loads(grid_data_json)
            
            # Create template from builder data
            template = GridTemplate.objects.create(
                name=form.cleaned_data['name'],
                description=form.cleaned_data['description'],
                grid_size=form.cleaned_data['grid_size'],
                difficulty=form.cleaned_data['difficulty'],
                grid_data=grid_data_parsed['grid_data'],
                created_by=request.user
            )
            
            # Create associated ShapeGame with solution data
            shape_game = ShapeGame.objects.create(
                name=f"{template.name} - Game",
                description=f"Auto-generated game for template: {template.name}",
                grid_template=template,
                solution_data=grid_data_parsed['solution_data'],
                created_by=request.user
            )
            
            # Add shapes that are used in the solution
            used_shape_ids = set()
            for answer_shape_id in grid_data_parsed['answer_data'].values():
                used_shape_ids.add(answer_shape_id)
            
            # Also add shapes used in fixed cells
            for row in grid_data_parsed['grid_data']:
                for cell in row:
                    if isinstance(cell, dict) and 'shapeId' in cell:
                        used_shape_ids.add(cell['shapeId'])
            
            for shape_id in used_shape_ids:
                try:
                    shape = Shape.objects.get(id=shape_id)
                    shape_game.available_shapes.add(shape)
                except Shape.DoesNotExist:
                    pass
            
            messages.success(request, f'Template "{template.name}" and associated game created successfully!')
            return redirect('games:manage_templates')
    else:
        form = GridTemplateBuilderForm()
    
    context = {
        'form': form,
        'page_title': 'Visual Grid Builder'
    }
    return render(request, 'games/admin/template_builder.html', context)

@user_passes_test(is_game_admin)
def template_edit_view(request, template_id):
    """Admin view for editing grid templates"""
    template = get_object_or_404(GridTemplate, id=template_id)
    
    if request.method == 'POST':
        form = GridTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, f'Template "{template.name}" updated successfully!')
            return redirect('games:manage_templates')
    else:
        form = GridTemplateForm(instance=template)
    
    context = {
        'form': form,
        'template': template,
        'page_title': f'Edit Template: {template.name}'
    }
    return render(request, 'games/admin/template_create.html', context)

# Shape Game Management Views

@user_passes_test(is_game_admin)
def shape_game_management_view(request):
    """Admin view for managing shape games"""
    games = ShapeGame.objects.all().order_by('-created_at')
    context = {
        'games': games,
        'page_title': 'Shape Game Management'
    }
    return render(request, 'games/admin/game_management.html', context)

@user_passes_test(is_game_admin)
def shape_game_create_view(request):
    """Redirect to Visual Puzzle Creator for modern game creation"""
    messages.info(request, 'Welcome to the enhanced Visual Puzzle Creator! Create amazing puzzles with drag-and-drop functionality.')
    return redirect('games:visual_puzzle_creator')

@user_passes_test(is_game_admin)
def shape_game_edit_view(request, game_id):
    """Admin view for editing shape games"""
    game = get_object_or_404(ShapeGame, id=game_id)
    
    if request.method == 'POST':
        form = ShapeGameForm(request.POST, instance=game)
        if form.is_valid():
            form.save()
            messages.success(request, f'Game "{game.name}" updated successfully!')
            return redirect('games:manage_shape_games')
    else:
        form = ShapeGameForm(instance=game)
    
    context = {
        'form': form,
        'game': game,
        'page_title': f'Edit Game: {game.name}'
    }
    return render(request, 'games/admin/game_create.html', context)

@user_passes_test(is_game_admin)
def shape_game_delete_view(request, game_id):
    """Admin view for deleting shape games"""
    game = get_object_or_404(ShapeGame, id=game_id)
    
    if request.method == 'POST':
        game_name = game.name
        game.delete()
        messages.success(request, f'Game "{game_name}" deleted successfully!')
        return redirect('games:manage_shape_games')
    
    context = {
        'game': game,
        'page_title': f'Delete Game: {game.name}'
    }
    return render(request, 'games/admin/shape_game_confirm_delete.html', context)

# User-facing Shape Game Views

def shape_game_list_view(request):
    """List available shape games for all users"""
    from django.db.models import Count, Q
    
    games = ShapeGame.objects.filter(is_active=True).annotate(
        total_attempts=Count('attempts'),
        completed_attempts=Count('attempts', filter=Q(attempts__status='completed'))
    ).order_by('-created_at')
    
    # Filter by difficulty if specified
    difficulty = request.GET.get('difficulty')
    if difficulty:
        games = games.filter(grid_template__difficulty=difficulty)
    
    context = {
        'games': games,
        'selected_difficulty': difficulty,
        'page_title': 'Shape Puzzle Games'
    }
    return render(request, 'games/shape_game_list.html', context)

@login_required
def play_shape_game_view(request, game_id):
    """Play a specific shape game"""
    game = get_object_or_404(ShapeGame, id=game_id, is_active=True)
    
    # Get or create game attempt
    attempt, created = ShapeGameAttempt.objects.get_or_create(
        user=request.user,
        shape_game=game,
        status=GameStatus.IN_PROGRESS,
        defaults={'current_state': {}}
    )
    
    context = {
        'game': game,
        'attempt': attempt,
        'template': game.grid_template,
        'shapes': game.available_shapes.all(),
        'grid_data': json.dumps(game.grid_template.grid_data),
        'current_state': json.dumps(attempt.current_state),
        'page_title': f'Play: {game.name}'
    }
    return render(request, 'games/play_shape_game.html', context)

# Shape Game API Endpoints

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_save_shape_game_state(request, game_id):
    """Save current state of shape game"""
    try:
        game = get_object_or_404(ShapeGame, id=game_id, is_active=True)
        
        # Get or create current attempt
        attempt, created = ShapeGameAttempt.objects.get_or_create(
            user=request.user,
            shape_game=game,
            status=GameStatus.IN_PROGRESS,
            defaults={'current_state': {}}
        )
        
        # Update state
        data = request.data
        attempt.current_state = data.get('current_state', {})
        attempt.score = data.get('score', 0)
        
        # Calculate placement counts
        placements = attempt.current_state
        attempt.correct_placements = len(placements)
        attempt.incorrect_placements = 0  # Will be calculated during validation
        
        # Update status if completed
        if data.get('status') == 'completed':
            attempt.status = GameStatus.COMPLETED
            attempt.end_time = timezone.now()
            attempt.time_taken_seconds = int((attempt.end_time - attempt.start_time).total_seconds())
            
            # Validate final solution
            validation_result = validate_shape_placement(game, placements)
            attempt.accuracy = validation_result['accuracy']
            attempt.score = validation_result['final_score']
            attempt.correct_placements = validation_result['correct_count']
            attempt.incorrect_placements = validation_result['incorrect_count']
        
        attempt.save()
        
        return Response({
            'success': True,
            'attempt_id': str(attempt.id),
            'score': attempt.score,
            'accuracy': attempt.accuracy
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_validate_shape_placement(request):
    """Validate shape placement in real-time"""
    try:
        game_id = request.data.get('game_id')
        placements = request.data.get('placements', {})
        
        game = get_object_or_404(ShapeGame, id=game_id, is_active=True)
        
        # Validate placement
        result = validate_shape_placement(game, placements)
        
        return Response({
            'success': True,
            'validation': result
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

def validate_shape_placement(game, placements):
    """
    Validate shape placements against the game solution
    Returns validation results with scoring
    """
    try:
        solution = game.solution_data
        grid_template = game.grid_template
        grid_data = grid_template.grid_data
        
        # Count total question cells
        total_questions = 0
        for row in grid_data:
            for cell in row:
                if cell == '?':
                    total_questions += 1
        
        correct_count = 0
        incorrect_count = 0
        validation_details = {}
        
        # Check each placement
        for position, placement in placements.items():
            expected_shape_id = solution.get(position)
            placed_shape_id = placement.get('shapeId')
            
            is_correct = expected_shape_id == placed_shape_id
            validation_details[position] = {
                'correct': is_correct,
                'expected': expected_shape_id,
                'placed': placed_shape_id
            }
            
            if is_correct:
                correct_count += 1
            else:
                incorrect_count += 1
        
        # Calculate accuracy
        if total_questions > 0:
            accuracy = (correct_count / total_questions) * 100
        else:
            accuracy = 0
        
        # Calculate score
        correct_points = correct_count * game.points_per_correct
        penalty_points = incorrect_count * game.penalty_per_wrong
        final_score = max(0, correct_points - penalty_points)
        
        return {
            'accuracy': round(accuracy, 2),
            'final_score': final_score,
            'correct_count': correct_count,
            'incorrect_count': incorrect_count,
            'total_questions': total_questions,
            'is_complete': len(placements) == total_questions,
            'is_perfect': incorrect_count == 0 and len(placements) == total_questions,
            'validation_details': validation_details
        }
        
    except Exception as e:
        return {
            'accuracy': 0,
            'final_score': 0,
            'correct_count': 0,
            'incorrect_count': 0,
            'total_questions': 0,
            'is_complete': False,
            'is_perfect': False,
            'error': str(e)
        }

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_shape_game_hint(request, game_id):
    """Provide hint for shape game"""
    try:
        game = get_object_or_404(ShapeGame, id=game_id, is_active=True)
        
        # Get current attempt
        attempt = ShapeGameAttempt.objects.filter(
            user=request.user,
            shape_game=game,
            status=GameStatus.IN_PROGRESS
        ).first()
        
        if not attempt:
            return Response({
                'success': False,
                'error': 'No active game session found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Find first unplaced question cell
        solution = game.solution_data
        current_placements = attempt.current_state
        grid_data = game.grid_template.grid_data
        
        hint_position = None
        hint_shape_id = None
        
        for row in range(len(grid_data)):
            for col in range(len(grid_data[row])):
                if grid_data[row][col] == '?':
                    position = f"{row},{col}"
                    if position not in current_placements:
                        hint_position = position
                        hint_shape_id = solution.get(position)
                        break
            if hint_position:
                break
        
        if hint_position and hint_shape_id:
            # Get shape details
            shape = Shape.objects.get(id=hint_shape_id)
            
            return Response({
                'success': True,
                'hint': {
                    'position': hint_position,
                    'shape_id': hint_shape_id,
                    'shape_name': shape.name,
                    'shape_type': shape.shape_type,
                    'message': f"Try placing the {shape.name} at the highlighted position!"
                }
            })
        else:
            return Response({
                'success': True,
                'hint': {
                    'message': "All question cells are filled!"
                }
            })
            
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# Level-based Progression Views for Users

@login_required
def level_list_view(request):
    """Display all levels and user progress through them"""
    from .models import PuzzleLevel, UserLevelProgress
    
    user = request.user
    
    # Get all levels with user progress
    levels = PuzzleLevel.objects.filter(is_active=True).order_by('level_number')
    level_data = []
    
    completed_levels = 0
    total_stars = 0
    current_level = 1
    
    for level in levels:
        # Check if level is unlocked
        is_unlocked = level.is_unlocked_for_user(user)
        
        # Get user progress for this level
        progress = UserLevelProgress.objects.filter(user=user, level=level).first()
        
        if progress and progress.is_completed:
            completed_levels += 1
            total_stars += progress.stars_earned if hasattr(progress, 'stars_earned') else 0
        elif is_unlocked and not progress:
            current_level = level.level_number
        
        level_data.append({
            'level': level,
            'is_unlocked': is_unlocked,
            'progress': progress,
            'completion_percentage': progress.completion_percentage if progress else 0,
        })
    
    context = {
        'page_title': 'Puzzle Levels',
        'level_data': level_data,
        'completed_levels': completed_levels,
        'total_levels': levels.count(),
        'current_level': current_level,
        'total_stars': total_stars,
    }
    
    return render(request, 'games/level_list.html', context)


@login_required
def level_detail_view(request, level_id):
    """Display puzzles in a specific level"""
    from .models import PuzzleLevel, UserLevelProgress, LevelPuzzle, UserPuzzleAttempt
    
    user = request.user
    level = get_object_or_404(PuzzleLevel, id=level_id, is_active=True)
    
    # Check if level is unlocked for user
    if not level.is_unlocked_for_user(user):
        messages.error(request, f'Level {level.level_number} is not yet unlocked. Complete previous levels first.')
        return redirect('games:level_list')
    
    # Get or create user progress for this level
    progress, created = UserLevelProgress.objects.get_or_create(
        user=user,
        level=level,
        defaults={'puzzles_completed': 0, 'is_completed': False}
    )
    
    # Get all puzzles in this level
    level_puzzles = LevelPuzzle.objects.filter(
        level=level, 
        is_active=True
    ).select_related('shape_game').order_by('order_in_level')
    
    # Add user attempt data to each puzzle
    puzzle_data = []
    for level_puzzle in level_puzzles:
        attempt = UserPuzzleAttempt.objects.filter(
            user=user,
            level_puzzle=level_puzzle
        ).first()
        
        puzzle_data.append({
            'level_puzzle': level_puzzle,
            'attempted': attempt is not None,
            'completed': attempt.is_completed if attempt else False,
            'score': attempt.score_earned if attempt else 0,
            'completion_time': attempt.shape_game_attempt.time_taken_seconds if attempt and attempt.shape_game_attempt else None,
        })
    
    context = {
        'page_title': f'Level {level.level_number}: {level.name}',
        'level': level,
        'progress': progress,
        'puzzle_data': puzzle_data,
    }
    
    return render(request, 'games/level_detail.html', context)


@login_required
def level_puzzle_play_view(request, level_id, puzzle_id):
    """Play a specific puzzle within a level"""
    from .models import PuzzleLevel, LevelPuzzle, UserPuzzleAttempt
    
    user = request.user
    level = get_object_or_404(PuzzleLevel, id=level_id, is_active=True)
    level_puzzle = get_object_or_404(LevelPuzzle, id=puzzle_id, level=level, is_active=True)
    
    # Check if level is unlocked
    if not level.is_unlocked_for_user(user):
        messages.error(request, f'Level {level.level_number} is not yet unlocked.')
        return redirect('games:level_list')
    
    # Check if user has already completed this puzzle
    existing_attempt = UserPuzzleAttempt.objects.filter(
        user=user,
        level_puzzle=level_puzzle,
        is_completed=True
    ).first()
    
    if existing_attempt:
        messages.info(request, 'You have already completed this puzzle!')
        return redirect('games:level_detail', level_id=level.id)
    
    # Get or create shape game attempt
    shape_game_attempt, created = ShapeGameAttempt.objects.get_or_create(
        user=user,
        shape_game=level_puzzle.shape_game,
        status='in_progress',
        defaults={'current_state': {}}
    )
    
    # Create or get user puzzle attempt
    user_attempt, created = UserPuzzleAttempt.objects.get_or_create(
        user=user,
        level_puzzle=level_puzzle,
        defaults={
            'shape_game_attempt': shape_game_attempt,
            'is_completed': False,
            'score_earned': 0
        }
    )
    
    # If attempt exists but no shape_game_attempt, link them
    if not created and not user_attempt.shape_game_attempt:
        user_attempt.shape_game_attempt = shape_game_attempt
        user_attempt.save()
    
    context = {
        'page_title': f'{level_puzzle.shape_game.name} - Level {level.level_number}',
        'level': level,
        'level_puzzle': level_puzzle,
        'shape_game': level_puzzle.shape_game,
        'attempt': shape_game_attempt,
        'user_attempt': user_attempt,
        'return_url': f'/games/levels/{level.id}/',
    }
    
    return render(request, 'games/level_puzzle_play.html', context)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_level_puzzle(request, level_id, puzzle_id):
    """Complete a level puzzle and update progress"""
    from .models import PuzzleLevel, LevelPuzzle, UserPuzzleAttempt, UserLevelProgress
    
    user = request.user
    level = get_object_or_404(PuzzleLevel, id=level_id, is_active=True)
    level_puzzle = get_object_or_404(LevelPuzzle, id=puzzle_id, level=level, is_active=True)
    
    try:
        # Get user's attempt
        user_attempt = UserPuzzleAttempt.objects.filter(
            user=user,
            level_puzzle=level_puzzle
        ).first()
        
        if not user_attempt:
            return Response({
                'success': False,
                'error': 'No attempt found for this puzzle'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the shape game attempt
        shape_attempt = user_attempt.shape_game_attempt
        
        if shape_attempt.status != 'completed':
            return Response({
                'success': False,
                'error': 'Shape game not completed yet'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate score and complete the level attempt
        score = shape_attempt.score
        user_attempt.complete_attempt(score)
        
        # Check if level is completed
        level_progress = UserLevelProgress.objects.get(user=user, level=level)
        level_completed = level_progress.is_completed
        
        # Check for achievements
        check_user_achievements(user)
        
        response_data = {
            'success': True,
            'score_earned': score,
            'level_progress': {
                'puzzles_completed': level_progress.puzzles_completed,
                'total_required': level.puzzles_required,
                'completion_percentage': level_progress.completion_percentage,
                'level_completed': level_completed
            }
        }
        
        if level_completed:
            response_data['message'] = f'Congratulations! You completed Level {level.level_number}!'
            response_data['next_level_unlocked'] = True
        
        return Response(response_data)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


def check_user_achievements(user):
    """Check and award achievements to user"""
    from .models import Achievement, UserAchievement, UserLevelProgress
    
    # Get user statistics
    completed_levels = UserLevelProgress.objects.filter(user=user, is_completed=True).count()
    total_puzzles = user.shape_game_attempts.filter(status='completed').count()
    total_score = user.total_score
    
    # Check each achievement type
    achievements_to_award = []
    
    # Check level-based achievements
    level_achievements = Achievement.objects.filter(
        requirement_type='levels_completed',
        requirement_value__lte=completed_levels,
        is_active=True
    )
    
    for achievement in level_achievements:
        if not UserAchievement.objects.filter(user=user, achievement=achievement).exists():
            achievements_to_award.append(achievement)
    
    # Check puzzle-based achievements
    puzzle_achievements = Achievement.objects.filter(
        requirement_type='puzzles_solved',
        requirement_value__lte=total_puzzles,
        is_active=True
    )
    
    for achievement in puzzle_achievements:
        if not UserAchievement.objects.filter(user=user, achievement=achievement).exists():
            achievements_to_award.append(achievement)
    
    # Check score-based achievements
    score_achievements = Achievement.objects.filter(
        requirement_type='score_reached',
        requirement_value__lte=total_score,
        is_active=True
    )
    
    for achievement in score_achievements:
        if not UserAchievement.objects.filter(user=user, achievement=achievement).exists():
            achievements_to_award.append(achievement)
    
    # Award achievements
    for achievement in achievements_to_award:
        UserAchievement.objects.create(user=user, achievement=achievement)
        user.total_score += achievement.points_reward
    
    if achievements_to_award:
        user.save()
    
    return achievements_to_award


@login_required
def user_achievements_view(request):
    """Display user's achievements"""
    from .models import UserAchievement, Achievement
    
    user = request.user
    
    # Get user's earned achievements
    earned_achievements = UserAchievement.objects.filter(
        user=user
    ).select_related('achievement').order_by('-earned_at')
    
    # Get available achievements not yet earned
    earned_ids = earned_achievements.values_list('achievement_id', flat=True)
    available_achievements = Achievement.objects.filter(
        is_active=True
    ).exclude(id__in=earned_ids).order_by('requirement_value')
    
    context = {
        'page_title': 'My Achievements',
        'earned_achievements': earned_achievements,
        'available_achievements': available_achievements,
        'total_earned': earned_achievements.count(),
        'total_available': Achievement.objects.filter(is_active=True).count(),
    }
    
    return render(request, 'games/user_achievements.html', context)


@user_passes_test(is_game_admin)
def shape_puzzle_creator_view(request):
    """Enhanced shape puzzle creator with step-by-step workflow"""
    if request.method == 'GET':
        context = {
            'page_title': 'Shape Puzzle Creator'
        }
        return render(request, 'games/admin/shape_puzzle_creator.html', context)

@csrf_exempt
@login_required
def create_shape_puzzle_api(request):
    """API endpoint to create shape puzzle and serve the puzzle creator page"""
    print(f"=== PUZZLE SAVE DEBUG ===")
    print(f"Method: {request.method}")
    print(f"User: {request.user}")
    print(f"User authenticated: {request.user.is_authenticated}")
    print(f"User is admin: {getattr(request.user, 'is_game_admin', False)}")
    print(f"User is staff: {request.user.is_staff}")
    print(f"Content-Type: {request.content_type}")
    print(f"Body: {request.body}")
    
    # Handle GET request - serve the puzzle creator page
    if request.method == 'GET':
        if not user_can_access_admin_features(request.user):
            return redirect('games:dashboard')
        
        context = {
            'page_title': 'Shape Puzzle Creator'
        }
        return render(request, 'games/admin/shape_puzzle_creator.html', context)
    
    # Handle POST request - API functionality
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Only GET and POST methods allowed'
        }, status=405)
    
    try:
        # Validate user is admin
        if not user_can_access_admin_features(request.user):
            print(f"Admin access check failed for user: {request.user}")
            return JsonResponse({
                'success': False,
                'message': 'Admin access required'
            }, status=403)
        
        print("Parsing JSON data...")
        # Parse JSON data
        data = json.loads(request.body)
        print(f"Parsed data: {data}")
        
        # Get form data
        puzzle_name = data.get('puzzle_name')
        puzzle_description = data.get('puzzle_description', '')
        puzzle_difficulty = data.get('puzzle_difficulty', 'easy')
        grid_size = int(data.get('grid_size'))
        grid_data = json.loads(data.get('grid_data'))
        solution_data = json.loads(data.get('solution_data'))
        shapes_used = json.loads(data.get('shapes_used'))
        
        print(f"Puzzle name: {puzzle_name}")
        print(f"Grid size: {grid_size}")
        
        # Validate required fields
        if not puzzle_name:
            return JsonResponse({
                'success': False,
                'message': 'Puzzle name is required'
            }, status=400)
        
        # Validate grid size
        if grid_size not in [3, 4, 5]:
            return JsonResponse({
                'success': False,
                'message': 'Invalid grid size. Must be 3, 4, or 5.'
            }, status=400)
        
        # Create grid template
        template = GridTemplate.objects.create(
            name=f"{puzzle_name} - Template",
            description=puzzle_description,
            grid_size=grid_size,
            grid_data=grid_data,
            difficulty=puzzle_difficulty,
            created_by=request.user
        )
        
        # Create shape game
        shape_game = ShapeGame.objects.create(
            name=puzzle_name,
            description=puzzle_description,
            grid_template=template,
            solution_data=solution_data,
            max_time_minutes=30,  # Default time
            points_per_correct=10,
            penalty_per_wrong=5,
            created_by=request.user
        )
        
        # Add shapes to the game
        if shapes_used:
            shapes = Shape.objects.filter(id__in=shapes_used)
            shape_game.available_shapes.set(shapes)
        
        # Auto-assign to next available level or create new level
        
        # Find the highest level number
        last_level = PuzzleLevel.objects.filter(is_active=True).order_by('-level_number').first()
        next_level_number = (last_level.level_number + 1) if last_level else 1
        
        # Create or get level
        level, created = PuzzleLevel.objects.get_or_create(
            level_number=next_level_number,
            defaults={
                'name': f"Level {next_level_number}",
                'description': f"Shape puzzles for level {next_level_number}",
                'puzzles_required': 1,  # Start with 1 puzzle per level
                'created_by': request.user
            }
        )
        
        # Create level puzzle assignment
        level_puzzle = LevelPuzzle.objects.create(
            level=level,
            shape_game=shape_game,
            order_in_level=1,
            points_reward=100
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Shape puzzle "{puzzle_name}" created successfully!',
            'game_id': shape_game.id,
            'level_id': level.id,
            'template_id': template.id
        })
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        print(f"Exception in create_shape_puzzle_api: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'message': f'Error creating puzzle: {str(e)}'
        }, status=500)


# API Views for AJAX requests

def api_shapes_list(request):
    """API endpoint to get list of available shapes"""
    try:
        shapes = Shape.objects.filter(is_active=True).order_by('shape_type', 'name')
        shapes_data = []
        
        for shape in shapes:
            shapes_data.append({
                'id': shape.id,
                'name': shape.name,
                'shape_type': shape.shape_type,
                'color': shape.color,
                'svg_data': shape.svg_data,
            })
        
        return JsonResponse(shapes_data, safe=False)
        
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=500
        )


@user_passes_test(lambda u: u.is_game_admin, login_url='/auth/login/')
def reference_puzzle_view(request):
    """
    Direct view to test the reference image puzzle
    """
    try:
        # Get the reference puzzle we just created
        reference_game = ShapeGame.objects.get(name='Reference Image Puzzle')
        
        # Create a new game session for testing
        if request.user.is_authenticated:
            game_session = ShapeGameAttempt.objects.create(
                user=request.user,
                shape_game=reference_game
            )
        else:
            # For anonymous users, create a temporary session
            game_session = None
            
        context = {
            'shape_game': reference_game,
            'game_session': game_session,
            'grid_template': reference_game.grid_template,
            'available_shapes': reference_game.available_shapes.filter(is_active=True),
            'grid_data': reference_game.grid_template.grid_data,
            'solution_data': reference_game.solution_data,
            'max_time': reference_game.max_time_minutes,
            'points_per_correct': reference_game.points_per_correct,
            'penalty_per_wrong': reference_game.penalty_per_wrong,
        }
        
        return render(request, 'games/reference_puzzle_play.html', context)
        
    except ShapeGame.DoesNotExist:
        messages.error(request, 'Reference puzzle not found. Please run the create_reference_puzzle command first.')
        return redirect('games:dashboard')


@user_passes_test(lambda u: u.is_game_admin, login_url='/auth/login/')
@admin_required
def visual_puzzle_creator_view(request):
    """
    Enhanced visual puzzle creator with drag and drop interface
    """
    from .models import PuzzleLevel
    
    context = {
        'page_title': 'Visual Puzzle Creator',
        'shapes': Shape.objects.filter(is_active=True),
        'levels': PuzzleLevel.objects.filter(is_active=True).order_by('level_number')
    }
    return render(request, 'games/admin/visual_puzzle_creator.html', context)

def test_shapes_view(request):
    """Simple test page to verify shapes API"""
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_shapes.html')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/html')
    except FileNotFoundError:
        return HttpResponse('<h1>Test file not found</h1>', content_type='text/html')
