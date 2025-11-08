from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    SudokuPuzzle, GameSession, Leaderboard, Achievement,
    Shape, GridTemplate, ShapeGame, ShapeGameAttempt,
    PuzzleLevel, LevelPuzzle, UserLevelProgress, UserPuzzleAttempt, UserAchievement
)

@admin.register(SudokuPuzzle)
class SudokuPuzzleAdmin(admin.ModelAdmin):
    list_display = ('id', 'difficulty', 'created_at', 'created_by', 'is_active')
    list_filter = ('difficulty', 'is_active', 'created_at')
    search_fields = ('id', 'created_by__username')
    readonly_fields = ('created_at',)
    
@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'puzzle', 'status', 'score', 'start_time', 'duration')
    list_filter = ('status', 'puzzle__difficulty', 'start_time')
    search_fields = ('user__username', 'puzzle__id')
    readonly_fields = ('start_time', 'duration')

@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ('user', 'difficulty', 'best_score', 'best_time', 'achieved_at')
    list_filter = ('difficulty', 'achieved_at')
    search_fields = ('user__username',)

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'requirement_type', 'requirement_value', 'points_reward', 'is_active')
    list_filter = ('requirement_type', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Achievement Information', {
            'fields': ('name', 'description', 'icon')
        }),
        ('Requirements', {
            'fields': ('requirement_type', 'requirement_value', 'points_reward')
        }),
        ('Metadata', {
            'fields': ('created_at', 'is_active'),
            'classes': ('collapse',)
        })
    )

# Shape-based Game Admin Classes

@admin.register(Shape)
class ShapeAdmin(admin.ModelAdmin):
    list_display = ('name', 'shape_type', 'color', 'svg_preview', 'created_at', 'created_by')
    list_filter = ('shape_type', 'created_at')
    search_fields = ('name', 'created_by__username')
    readonly_fields = ('created_at', 'svg_preview')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'shape_type', 'color', 'created_by')
        }),
        ('Shape Data', {
            'fields': ('svg_data', 'image', 'svg_preview'),
            'description': 'Upload SVG data for the shape. The preview will be generated automatically.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'is_active'),
            'classes': ('collapse',)
        })
    )
    
    def svg_preview(self, obj):
        if obj.svg_data:
            return mark_safe(f'<div style="width: 100px; height: 100px; border: 1px solid #ccc;">{obj.svg_data}</div>')
        return "No SVG data"
    svg_preview.short_description = "SVG Preview"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(GridTemplate)
class GridTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'grid_size', 'difficulty', 'grid_preview', 'created_at', 'created_by')
    list_filter = ('grid_size', 'difficulty', 'created_at')
    search_fields = ('name', 'created_by__username')
    readonly_fields = ('created_at', 'grid_preview', 'question_cell_count')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'difficulty', 'created_by')
        }),
        ('Grid Configuration', {
            'fields': ('grid_size', 'grid_data', 'grid_preview', 'question_cell_count'),
            'description': 'Define the grid layout using JSON format. Use "?" for question mark cells and 0 for empty cells.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'is_active'),
            'classes': ('collapse',)
        })
    )
    
    def grid_preview(self, obj):
        if obj.grid_data:
            try:
                grid = obj.grid_data
                html = '<table style="border-collapse: collapse; font-size: 12px;">'
                for row in grid:
                    html += '<tr>'
                    for cell in row:
                        style = 'border: 1px solid #333; width: 20px; height: 20px; text-align: center;'
                        if cell == '?':
                            style += ' background-color: #fff3cd;'
                        html += f'<td style="{style}">{cell}</td>'
                    html += '</tr>'
                html += '</table>'
                return mark_safe(html)
            except:
                return "Invalid grid data"
        return "No grid data"
    grid_preview.short_description = "Grid Preview"
    
    def question_cell_count(self, obj):
        return obj.question_cell_count
    question_cell_count.short_description = "Question Cells"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(ShapeGame)
class ShapeGameAdmin(admin.ModelAdmin):
    list_display = ('name', 'grid_template', 'get_difficulty', 'attempt_count', 'completion_rate', 'created_at', 'created_by')
    list_filter = ('grid_template__difficulty', 'created_at')
    search_fields = ('name', 'created_by__username')
    readonly_fields = ('created_at', 'attempt_count', 'completion_rate')
    filter_horizontal = ('available_shapes',)
    fieldsets = (
        ('Game Information', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Game Configuration', {
            'fields': ('grid_template', 'available_shapes', 'solution_data')
        }),
        ('Game Settings', {
            'fields': ('max_time_minutes', 'points_per_correct', 'penalty_per_wrong')
        }),
        ('Statistics', {
            'fields': ('attempt_count', 'completion_rate'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'is_active'),
            'classes': ('collapse',)
        })
    )
    
    def get_difficulty(self, obj):
        return obj.grid_template.difficulty
    get_difficulty.short_description = "Difficulty"
    
    def attempt_count(self, obj):
        return obj.attempts.count()
    attempt_count.short_description = "Total Attempts"
    
    def completion_rate(self, obj):
        total = obj.attempts.count()
        if total == 0:
            return "No attempts"
        completed = obj.attempts.filter(status='completed').count()
        rate = (completed / total) * 100
        return f"{rate:.1f}% ({completed}/{total})"
    completion_rate.short_description = "Completion Rate"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(ShapeGameAttempt)
class ShapeGameAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'shape_game', 'status', 'score', 'accuracy', 'start_time', 'duration')
    list_filter = ('status', 'shape_game__grid_template__difficulty', 'start_time')
    search_fields = ('user__username', 'shape_game__name')
    readonly_fields = ('start_time', 'duration', 'accuracy_display')
    fieldsets = (
        ('Attempt Information', {
            'fields': ('user', 'shape_game', 'status')
        }),
        ('Game State', {
            'fields': ('current_state',),
            'description': 'JSON data representing shape placements on the grid.'
        }),
        ('Results', {
            'fields': ('score', 'accuracy', 'accuracy_display', 'correct_placements', 'incorrect_placements', 'time_taken_seconds'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('start_time', 'end_time', 'duration'),
            'classes': ('collapse',)
        })
    )
    
    def accuracy_display(self, obj):
        return f"{obj.accuracy:.1f}%"
    accuracy_display.short_description = "Accuracy"
    
    def duration(self, obj):
        if obj.end_time:
            delta = obj.end_time - obj.start_time
            return f"{delta.total_seconds():.0f} seconds"
        return "In progress"
    duration.short_description = "Duration"


# Level-based Progression Admin Classes

@admin.register(PuzzleLevel)
class PuzzleLevelAdmin(admin.ModelAdmin):
    list_display = ('level_number', 'name', 'puzzles_required', 'total_puzzles_assigned', 'users_started', 'users_completed', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'total_puzzles_assigned', 'users_started', 'users_completed')
    fieldsets = (
        ('Level Information', {
            'fields': ('level_number', 'name', 'description', 'created_by')
        }),
        ('Level Requirements', {
            'fields': ('puzzles_required', 'unlock_level')
        }),
        ('Statistics', {
            'fields': ('total_puzzles_assigned', 'users_started', 'users_completed'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'is_active'),
            'classes': ('collapse',)
        })
    )
    
    def total_puzzles_assigned(self, obj):
        return obj.level_puzzles.filter(is_active=True).count()
    total_puzzles_assigned.short_description = "Puzzles Assigned"
    
    def users_started(self, obj):
        return obj.user_progress.count()
    users_started.short_description = "Users Started"
    
    def users_completed(self, obj):
        return obj.user_progress.filter(is_completed=True).count()
    users_completed.short_description = "Users Completed"


@admin.register(LevelPuzzle)
class LevelPuzzleAdmin(admin.ModelAdmin):
    list_display = ('level', 'shape_game', 'order_in_level', 'points_reward', 'attempts_count', 'is_active')
    list_filter = ('level', 'is_active', 'created_at')
    search_fields = ('level__name', 'shape_game__name')
    readonly_fields = ('created_at', 'attempts_count')
    
    def attempts_count(self, obj):
        return obj.attempts.count()
    attempts_count.short_description = "Total Attempts"


@admin.register(UserLevelProgress)
class UserLevelProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'puzzles_completed', 'completion_percentage', 'total_score', 'is_completed')
    list_filter = ('level', 'is_completed', 'started_at')
    search_fields = ('user__username', 'level__name')
    readonly_fields = ('started_at', 'completion_percentage')
    
    def completion_percentage(self, obj):
        return f"{obj.completion_percentage:.1f}%"
    completion_percentage.short_description = "Completion %"


@admin.register(UserPuzzleAttempt)
class UserPuzzleAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'level_puzzle', 'is_completed', 'score_earned', 'completed_at')
    list_filter = ('is_completed', 'level_puzzle__level', 'completed_at')
    search_fields = ('user__username', 'level_puzzle__shape_game__name')
    readonly_fields = ('completed_at',)


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'earned_at')
    list_filter = ('achievement__requirement_type', 'earned_at')
    search_fields = ('user__username', 'achievement__name')
    readonly_fields = ('earned_at',)
