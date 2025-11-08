from django.urls import path
from . import views, level_admin_views

app_name = 'games'

urlpatterns = [
    # Main game URLs
    path('', views.home_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('puzzles/', views.puzzle_list_view, name='puzzle_list'),
    path('puzzles/<int:puzzle_id>/play/', views.play_puzzle_view, name='play_puzzle'),
    path('puzzles/create/', views.create_puzzle_view, name='create_puzzle'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    
    # Level-based Progression URLs (for users)
    path('levels/', views.level_list_view, name='level_list'),
    path('levels/<int:level_id>/', views.level_detail_view, name='level_detail'),
    path('levels/<int:level_id>/play/', views.level_detail_view, name='level_play'),  # Alias for level_detail
    path('levels/<int:level_id>/puzzles/<int:puzzle_id>/play/', views.level_puzzle_play_view, name='level_puzzle_play'),
    path('achievements/', views.user_achievements_view, name='user_achievements'),
    
    # Shape Game URLs
    path('shape-games/', views.shape_game_list_view, name='shape_game_list'),
    path('shape-games/<int:game_id>/play/', views.play_shape_game_view, name='play_shape_game'),
    
    # Admin URLs - Shape Management
    path('manage/shapes/', views.shape_management_view, name='manage_shapes'),
    path('manage/shapes/upload/', views.shape_upload_view, name='shape_upload'),
    path('manage/shapes/<int:shape_id>/edit/', views.shape_edit_view, name='shape_edit'),
    path('manage/shapes/<int:shape_id>/delete/', views.shape_delete_view, name='shape_delete'),
    
    # Admin URLs - Template Management
    path('manage/templates/', views.template_management_view, name='manage_templates'),
    path('manage/templates/create/', views.template_create_view, name='template_create'),
    path('manage/templates/builder/', views.template_builder_view, name='template_builder'),
    path('manage/templates/<int:template_id>/edit/', views.template_edit_view, name='template_edit'),
    
    # Admin URLs - Shape Game Management
    path('manage/shape-games/', views.shape_game_management_view, name='manage_shape_games'),
    path('manage/shape-games/create/', views.shape_game_create_view, name='shape_game_create'),
    path('manage/shape-games/<int:game_id>/edit/', views.shape_game_edit_view, name='shape_game_edit'),
    path('manage/shape-games/<int:game_id>/delete/', views.shape_game_delete_view, name='shape_game_delete'),
    path('create-shape-puzzle/', views.create_shape_puzzle_api, name='create_shape_puzzle'),
    path('visual-puzzle-creator/', views.visual_puzzle_creator_view, name='visual_puzzle_creator'),
    path('reference-puzzle/', views.reference_puzzle_view, name='reference_puzzle'),
    path('test-shapes/', views.test_shapes_view, name='test_shapes'),
    
    # Admin URLs - Level Management
    path('manage/levels/', level_admin_views.level_management_view, name='level_management'),
    path('manage/levels/create/', level_admin_views.create_level_view, name='create_level'),
    path('manage/levels/<int:level_id>/edit/', level_admin_views.edit_level_view, name='edit_level'),
    path('manage/levels/<int:level_id>/', level_admin_views.level_detail_view, name='admin_level_detail'),
    path('manage/levels/<int:level_id>/assign-puzzle/', level_admin_views.assign_puzzle_to_level, name='assign_puzzle_to_level'),
    path('manage/levels/<int:level_id>/remove-puzzle/<int:puzzle_id>/', level_admin_views.remove_puzzle_from_level, name='remove_puzzle_from_level'),
    path('manage/user-progress/', level_admin_views.user_level_progress_view, name='user_level_progress'),
    path('manage/user-progress/<int:user_id>/<int:level_id>/reset/', level_admin_views.reset_user_progress, name='reset_user_progress'),
    path('manage/achievements/', level_admin_views.achievement_management_view, name='achievement_management'),
    path('manage/achievements/create/', level_admin_views.create_achievement_view, name='create_achievement'),
    path('manage/game-stats/', level_admin_views.user_game_stats_view, name='user_game_stats'),
    path('manage/levels/bulk-actions/', level_admin_views.bulk_level_operations, name='bulk_level_operations'),
    
    # API endpoints
    path('api/puzzles/', views.api_puzzle_list, name='api_puzzle_list'),
    path('api/puzzles/<int:puzzle_id>/session/', views.api_game_session, name='api_game_session'),
    path('api/sessions/<int:session_id>/save/', views.api_save_game_state, name='api_save_game_state'),
    path('api/validate-move/', views.api_validate_move, name='api_validate_move'),
    path('api/shapes/', views.api_shapes_list, name='api_shapes_list'),
    # Shape Game API endpoints
    path('api/shape-games/<int:game_id>/save-state/', views.api_save_shape_game_state, name='api_save_shape_game_state'),
    path('api/shape-games/validate-placement/', views.api_validate_shape_placement, name='api_validate_shape_placement'),
    path('api/shape-games/<int:game_id>/hint/', views.api_shape_game_hint, name='api_shape_game_hint'),
    
    # Level-based API endpoints
    path('api/levels/<int:level_id>/puzzles/<int:puzzle_id>/complete/', views.complete_level_puzzle, name='complete_level_puzzle'),
]