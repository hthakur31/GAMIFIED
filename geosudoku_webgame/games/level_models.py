from django.db import models
from django.conf import settings
from authentication.models import User

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


class LevelPuzzle(models.Model):
    """
    Links puzzles to specific levels in the progression system.
    """
    level = models.ForeignKey(PuzzleLevel, on_delete=models.CASCADE, related_name='level_puzzles')
    shape_game = models.ForeignKey('games.ShapeGame', on_delete=models.CASCADE, related_name='level_assignments')
    order_in_level = models.PositiveIntegerField(default=1)
    points_reward = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['level', 'order_in_level']
        unique_together = ['level', 'shape_game']
        
    def __str__(self):
        return f"{self.level.name} - {self.shape_game.name} (#{self.order_in_level})"


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
            self.completed_at = models.timezone.now()
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


class UserPuzzleAttempt(models.Model):
    """
    Tracks individual puzzle attempts within the level system.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='puzzle_attempts')
    level_puzzle = models.ForeignKey(LevelPuzzle, on_delete=models.CASCADE, related_name='attempts')
    shape_game_attempt = models.OneToOneField(
        'games.ShapeGameAttempt', 
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
            self.completed_at = models.timezone.now()
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


class Achievement(models.Model):
    """
    System achievements users can earn
    """
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, default='trophy')  # Bootstrap icon name
    points_reward = models.PositiveIntegerField(default=50)
    requirement_type = models.CharField(max_length=50, choices=[
        ('levels_completed', 'Levels Completed'),
        ('puzzles_solved', 'Puzzles Solved'),
        ('score_reached', 'Score Reached'),
        ('streak', 'Consecutive Wins'),
        ('speed', 'Speed Completion'),
    ])
    requirement_value = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    """
    Tracks achievements earned by users
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='earned_by')
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'achievement']
        ordering = ['-earned_at']
        
    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"