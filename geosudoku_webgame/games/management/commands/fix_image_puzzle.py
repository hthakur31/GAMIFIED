from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from games.models import Shape, GridTemplate, ShapeGame, PuzzleLevel, LevelPuzzle
import json

User = get_user_model()

class Command(BaseCommand):
    help = 'Fix the image puzzle with correct grid data'

    def handle(self, *args, **options):
        # Get admin user
        admin_user = User.objects.filter(role='ADMIN').first()
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True).first()
        
        if not admin_user:
            self.stdout.write(self.style.ERROR('No admin user found.'))
            return

        # Get the existing shapes
        green_circle = Shape.objects.get(name='Green Circle')
        blue_triangle = Shape.objects.get(name='Blue Triangle')
        red_square = Shape.objects.get(name='Red Square')
        
        self.stdout.write(f'Found shapes: {green_circle.id}, {blue_triangle.id}, {red_square.id}')

        # Update the grid template with correct data
        # Based on image: Row 1: Green circle(1), empty, empty
        #                 Row 2: empty, question mark(?), empty  
        #                 Row 3: Blue triangle(2), empty, Green circle(1)
        grid_data = [
            [green_circle.id, '?', '?'],  # Green circle, empty, empty
            ['?', '?', '?'],  # Empty, question mark, empty
            [blue_triangle.id, '?', green_circle.id]   # Blue triangle, empty, green circle
        ]

        # Update existing template
        template = GridTemplate.objects.get(name="3x3 Shape Pattern Puzzle")
        template.grid_data = grid_data
        template.save()
        
        self.stdout.write(f'Updated template with grid data: {grid_data}')

        # Update the shape game solution
        solution_data = {
            'grid': [
                [green_circle.id, red_square.id, blue_triangle.id],  # Green circle, Red square, Blue triangle
                [blue_triangle.id, green_circle.id, red_square.id],  # Blue triangle, Green circle, Red square  
                [blue_triangle.id, red_square.id, green_circle.id]   # Blue triangle, Red square, Green circle (from image)
            ],
            'explanation': 'Each row and column must contain each shape exactly once - like a Sudoku with shapes!'
        }

        # Update existing shape game
        shape_game = ShapeGame.objects.get(name="Image Pattern Puzzle")
        shape_game.solution_data = solution_data
        shape_game.save()
        
        self.stdout.write(f'Updated solution data: {solution_data}')

        self.stdout.write(
            self.style.SUCCESS('✅ Successfully fixed the puzzle data!')
        )