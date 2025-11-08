from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json
import random
import uuid

User = get_user_model()

class DifficultyLevel(models.TextChoices):
    EASY = 'easy', 'Easy'
    MEDIUM = 'medium', 'Medium'
    HARD = 'hard', 'Hard'
    EXPERT = 'expert', 'Expert'

class GameStatus(models.TextChoices):
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    ABANDONED = 'abandoned', 'Abandoned'

class ShapeType(models.TextChoices):
    CIRCLE = 'circle', 'Circle'
    SQUARE = 'square', 'Square'
    TRIANGLE = 'triangle', 'Triangle'
    DIAMOND = 'diamond', 'Diamond'
    STAR = 'star', 'Star'
    HEXAGON = 'hexagon', 'Hexagon'

# Level-based Progression System Models

class PuzzleLevel(models.Model):
    """
    Represents a level in the puzzle progression system.
    Each level contains a set of puzzles that users must complete.
    """
    level_number = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    puzzles_required = models.PositiveIntegerField(default=10)  # Number of puzzles to complete this level
    unlock_level = models.PositiveIntegerField(default=0)  # Which level needs to be completed to unlock this
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_levels')
    
    class Meta:
        ordering = ['level_number']
        
    def __str__(self):
        return f"Level {self.level_number}: {self.name}"
    
    @property
    def total_puzzles(self):
        """Get total number of puzzles in this level"""
        return self.level_puzzles.filter(is_active=True).count()
    
    def is_unlocked_for_user(self, user):
        """Check if this level is unlocked for a specific user"""
        if self.level_number == 1:  # First level is always unlocked
            return True
        
        # Check if previous level is completed
        previous_level = self.level_number - 1
        if previous_level <= 0:
            return True
            
        try:
            prev_level = PuzzleLevel.objects.get(level_number=previous_level)
            return UserLevelProgress.objects.filter(
                user=user,
                level=prev_level,
                is_completed=True
            ).exists()
        except PuzzleLevel.DoesNotExist:
            return True


class UserLevelProgress(models.Model):
    """
    Tracks user progress through the level system.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='level_progress')
    level = models.ForeignKey(PuzzleLevel, on_delete=models.CASCADE, related_name='user_progress')
    puzzles_completed = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_score = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ['user', 'level']
        ordering = ['level__level_number']
        
    def __str__(self):
        return f"{self.user.username} - {self.level.name} ({self.puzzles_completed}/{self.level.puzzles_required})"
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage for this level"""
        if self.level.puzzles_required == 0:
            return 100
        return min(100, (self.puzzles_completed / self.level.puzzles_required) * 100)
    
    def check_completion(self):
        """Check if level is completed and update status"""
        if self.puzzles_completed >= self.level.puzzles_required and not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
            self.save()
            
            # Unlock next level for user
            self.unlock_next_level()
            
    def unlock_next_level(self):
        """Unlock the next level for this user"""
        next_level_number = self.level.level_number + 1
        try:
            next_level = PuzzleLevel.objects.get(level_number=next_level_number, is_active=True)
            # Create progress record for next level if it doesn't exist
            UserLevelProgress.objects.get_or_create(
                user=self.user,
                level=next_level,
                defaults={'puzzles_completed': 0, 'is_completed': False}
            )
        except PuzzleLevel.DoesNotExist:
            pass  # No next level available


# New Shape-based Game Models

class Shape(models.Model):
    """
    Geometric shapes that can be used in games
    """
    name = models.CharField(max_length=100)
    shape_type = models.CharField(max_length=20, choices=ShapeType.choices)
    color = models.CharField(max_length=7, help_text="Hex color code (e.g., #FF0000)")
    svg_data = models.TextField(help_text="SVG path data for the shape")
    image = models.ImageField(upload_to='shapes/', blank=True, null=True, help_text="Optional image representation")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_shapes')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['shape_type', 'name']
        
    def __str__(self):
        return f"{self.name} ({self.shape_type})"

class GridTemplate(models.Model):
    """
    Grid templates created by admins with question mark cells
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    grid_size = models.IntegerField(default=9, help_text="Grid size (e.g., 9 for 9x9)")
    grid_data = models.JSONField(help_text="Grid layout with '?' for question cells and shape IDs for fixed cells")
    difficulty = models.CharField(max_length=10, choices=DifficultyLevel.choices, default=DifficultyLevel.EASY)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} ({self.grid_size}x{self.grid_size})"
    
    @property
    def question_cell_count(self):
        """Count the number of question mark cells"""
        count = 0
        for row in self.grid_data:
            for cell in row:
                if cell == '?':
                    count += 1
        return count

class ShapeGame(models.Model):
    """
    Complete shape-based games linking grid templates with available shapes
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    grid_template = models.ForeignKey(GridTemplate, on_delete=models.CASCADE, related_name='shape_games')
    available_shapes = models.ManyToManyField(Shape, related_name='games', help_text="Shapes available for this game")
    solution_data = models.JSONField(help_text="Complete solution showing which shapes go where")
    max_time_minutes = models.IntegerField(default=30, help_text="Maximum time allowed in minutes")
    points_per_correct = models.IntegerField(default=10, help_text="Points awarded per correct placement")
    penalty_per_wrong = models.IntegerField(default=5, help_text="Points deducted per wrong placement")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_shape_games')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name
    
    def calculate_max_score(self):
        """Calculate maximum possible score for this game"""
        if self.grid_template:
            return self.grid_template.question_cell_count * self.points_per_correct
        return 0


class LevelPuzzle(models.Model):
    """
    Links puzzles to specific levels in the progression system.
    """
    level = models.ForeignKey(PuzzleLevel, on_delete=models.CASCADE, related_name='level_puzzles')
    shape_game = models.ForeignKey(ShapeGame, on_delete=models.CASCADE, related_name='level_assignments')
    order_in_level = models.PositiveIntegerField(default=1)
    points_reward = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['level', 'order_in_level']
        unique_together = ['level', 'shape_game']
        
    def __str__(self):
        return f"{self.level.name} - {self.shape_game.name} (#{self.order_in_level})"


class ShapeGameAttempt(models.Model):
    """
    User attempts at shape games with results tracking
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shape_game_attempts')
    shape_game = models.ForeignKey(ShapeGame, on_delete=models.CASCADE, related_name='attempts')
    current_state = models.JSONField(help_text="Current placement of shapes", default=dict)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=GameStatus.choices, default=GameStatus.IN_PROGRESS)
    
    # Results tracking
    score = models.IntegerField(default=0)
    accuracy = models.FloatField(default=0.0, help_text="Percentage accuracy (0-100)")
    correct_placements = models.IntegerField(default=0)
    incorrect_placements = models.IntegerField(default=0)
    time_taken_seconds = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-start_time']
        
    def __str__(self):
        return f"{self.user.username} - {self.shape_game.name} - {self.status}"
    
    @property
    def duration_minutes(self):
        """Get duration in minutes"""
        if self.time_taken_seconds:
            return round(self.time_taken_seconds / 60, 2)
        return 0
    
    def calculate_accuracy(self):
        """Calculate accuracy percentage"""
        total_placements = self.correct_placements + self.incorrect_placements
        if total_placements == 0:
            return 0.0
        return round((self.correct_placements / total_placements) * 100, 2)
    
    def calculate_score(self):
        """Calculate final score based on correct/incorrect placements"""
        correct_points = self.correct_placements * self.shape_game.points_per_correct
        penalty_points = self.incorrect_placements * self.shape_game.penalty_per_wrong
        return max(0, correct_points - penalty_points)


class UserPuzzleAttempt(models.Model):
    """
    Tracks individual puzzle attempts within the level system.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='puzzle_attempts')
    level_puzzle = models.ForeignKey(LevelPuzzle, on_delete=models.CASCADE, related_name='attempts')
    shape_game_attempt = models.OneToOneField(
        ShapeGameAttempt, 
        on_delete=models.CASCADE, 
        related_name='level_attempt'
    )
    is_completed = models.BooleanField(default=False)
    score_earned = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'level_puzzle']
        ordering = ['-completed_at']
        
    def __str__(self):
        return f"{self.user.username} - {self.level_puzzle}"
    
    def complete_attempt(self, score):
        """Mark attempt as completed and update user progress"""
        if not self.is_completed:
            self.is_completed = True
            self.score_earned = score
            self.completed_at = timezone.now()
            self.save()
            
            # Update user level progress
            level_progress, created = UserLevelProgress.objects.get_or_create(
                user=self.user,
                level=self.level_puzzle.level,
                defaults={'puzzles_completed': 0, 'is_completed': False}
            )
            
            level_progress.puzzles_completed += 1
            level_progress.total_score += score
            level_progress.save()
            
            # Check if level is completed
            level_progress.check_completion()
            
            # Update user total score
            self.user.total_score += score
            self.user.save()


# Original Sudoku Game Models (keeping existing functionality)

class SudokuPuzzle(models.Model):
    """
    Represents a Sudoku puzzle with geographic/regional constraints
    """
    difficulty = models.CharField(max_length=10, choices=DifficultyLevel.choices, default=DifficultyLevel.EASY)
    puzzle_data = models.JSONField(help_text="9x9 grid with initial numbers (0 for empty cells)")
    solution_data = models.JSONField(help_text="Complete solution for the puzzle")
    regions_data = models.JSONField(help_text="Geographic regions definition for GeoSudoku", default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_puzzles')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Puzzle {self.id} - {self.difficulty.title()}"
    
    @staticmethod
    def generate_basic_puzzle(difficulty='easy'):
        """
        Generate a basic Sudoku puzzle
        This is a simplified version - in production you'd want a more sophisticated algorithm
        """
        # This is a simplified puzzle generation - in a real app, you'd implement proper sudoku generation
        base_solution = [
            [5, 3, 4, 6, 7, 8, 9, 1, 2],
            [6, 7, 2, 1, 9, 5, 3, 4, 8],
            [1, 9, 8, 3, 4, 2, 5, 6, 7],
            [8, 5, 9, 7, 6, 1, 4, 2, 3],
            [4, 2, 6, 8, 5, 3, 7, 9, 1],
            [7, 1, 3, 9, 2, 4, 8, 5, 6],
            [9, 6, 1, 5, 3, 7, 2, 8, 4],
            [2, 8, 7, 4, 1, 9, 6, 3, 5],
            [3, 4, 5, 2, 8, 6, 1, 7, 9]
        ]
        
        # Shuffle the solution to create variation
        solution = [row[:] for row in base_solution]
        
        # Create puzzle by removing numbers based on difficulty
        puzzle = [row[:] for row in solution]
        cells_to_remove = {
            'easy': 35,
            'medium': 45,
            'hard': 55,
            'expert': 65
        }
        
        remove_count = cells_to_remove.get(difficulty, 35)
        positions = [(i, j) for i in range(9) for j in range(9)]
        random.shuffle(positions)
        
        for i in range(remove_count):
            row, col = positions[i]
            puzzle[row][col] = 0
        
        # Generate regions for GeoSudoku (this is simplified)
        regions = [
            {'name': 'North America', 'cells': [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)]},
            {'name': 'Europe', 'cells': [(0, 3), (0, 4), (0, 5), (1, 3), (1, 4), (1, 5), (2, 3), (2, 4), (2, 5)]},
            {'name': 'Asia', 'cells': [(0, 6), (0, 7), (0, 8), (1, 6), (1, 7), (1, 8), (2, 6), (2, 7), (2, 8)]},
            {'name': 'Africa', 'cells': [(3, 0), (3, 1), (3, 2), (4, 0), (4, 1), (4, 2), (5, 0), (5, 1), (5, 2)]},
            {'name': 'South America', 'cells': [(3, 3), (3, 4), (3, 5), (4, 3), (4, 4), (4, 5), (5, 3), (5, 4), (5, 5)]},
            {'name': 'Australia', 'cells': [(3, 6), (3, 7), (3, 8), (4, 6), (4, 7), (4, 8), (5, 6), (5, 7), (5, 8)]},
            {'name': 'Antarctica', 'cells': [(6, 0), (6, 1), (6, 2), (7, 0), (7, 1), (7, 2), (8, 0), (8, 1), (8, 2)]},
            {'name': 'Oceania', 'cells': [(6, 3), (6, 4), (6, 5), (7, 3), (7, 4), (7, 5), (8, 3), (8, 4), (8, 5)]},
            {'name': 'Arctic', 'cells': [(6, 6), (6, 7), (6, 8), (7, 6), (7, 7), (7, 8), (8, 6), (8, 7), (8, 8)]}
        ]
        
        return puzzle, solution, regions

class GameSession(models.Model):
    """
    Represents a game session for a user playing a puzzle
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='game_sessions')
    puzzle = models.ForeignKey(SudokuPuzzle, on_delete=models.CASCADE, related_name='game_sessions')
    current_state = models.JSONField(help_text="Current state of the game board")
    status = models.CharField(max_length=15, choices=GameStatus.choices, default=GameStatus.IN_PROGRESS)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(default=0)
    hints_used = models.IntegerField(default=0)
    mistakes_made = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-start_time']
        unique_together = ['user', 'puzzle']
    
    def __str__(self):
        return f"{self.user.username} - {self.puzzle} - {self.status}"
    
    @property
    def duration(self):
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    def calculate_score(self):
        """
        Calculate score based on difficulty, time, hints used, and mistakes
        """
        if self.status != GameStatus.COMPLETED:
            return 0
        
        base_scores = {
            'easy': 100,
            'medium': 200,
            'hard': 300,
            'expert': 500
        }
        
        base_score = base_scores.get(self.puzzle.difficulty, 100)
        
        # Deduct points for hints and mistakes
        penalty = (self.hints_used * 10) + (self.mistakes_made * 5)
        
        # Time bonus (if completed quickly)
        if self.duration:
            time_bonus = max(0, 100 - (self.duration.seconds // 60))  # 1 point per minute
        else:
            time_bonus = 0
        
        final_score = max(0, base_score + time_bonus - penalty)
        return final_score

class Leaderboard(models.Model):
    """
    Track top scores and achievements
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leaderboard_entries')
    difficulty = models.CharField(max_length=10, choices=DifficultyLevel.choices)
    best_score = models.IntegerField()
    best_time = models.DurationField()
    puzzle = models.ForeignKey(SudokuPuzzle, on_delete=models.CASCADE)
    achieved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-best_score', 'best_time']
        unique_together = ['user', 'difficulty']
    
    def __str__(self):
        return f"{self.user.username} - {self.difficulty}: {self.best_score}"

class Achievement(models.Model):
    """
    System achievements users can earn
    """
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, default='trophy')  # Bootstrap icon name
    points_reward = models.PositiveIntegerField(default=50)
    requirement_type = models.CharField(max_length=50, default='puzzles_solved', choices=[
        ('levels_completed', 'Levels Completed'),
        ('puzzles_solved', 'Puzzles Solved'),
        ('score_reached', 'Score Reached'),
        ('streak', 'Consecutive Wins'),
        ('speed', 'Speed Completion'),
        ('first_win', 'First Win'),
        ('speed_demon', 'Speed Demon'),
        ('perfectionist', 'Perfectionist'),
        ('puzzle_master', 'Puzzle Master'),
        ('region_expert', 'Region Expert'),
    ])
    requirement_value = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    """
    Tracks achievements earned by users
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='earned_by')
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'achievement']
        ordering = ['-earned_at']
        
    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"
