from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from games.models import Shape, ShapeGame, GridTemplate, PuzzleLevel, LevelPuzzle
import json

User = get_user_model()

class Command(BaseCommand):
    help = 'Create the specific puzzle shown in the reference image'

    def handle(self, *args, **options):
        # Get admin user
        admin_user = User.objects.filter(role='ADMIN').first()
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True).first()
        
        if not admin_user:
            self.stdout.write(
                self.style.ERROR('No admin user found. Please create an admin user first.')
            )
            return

        # Get the shapes we need for this puzzle
        try:
            green_circle = Shape.objects.filter(name__icontains='green', shape_type='circle').first()
            blue_triangle = Shape.objects.filter(name__icontains='blue', shape_type='triangle').first()
            red_square = Shape.objects.filter(name__icontains='red', shape_type='square').first()
            
            if not all([green_circle, blue_triangle, red_square]):
                self.stdout.write(
                    self.style.ERROR('Required shapes not found. Please run setup_default_shapes first.')
                )
                return
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error finding shapes: {e}')
            )
            return

        # Create grid template for 3x3
        grid_template, created = GridTemplate.objects.get_or_create(
            name='Reference Puzzle Grid',
            defaults={
                'grid_size': 3,
                'created_by': admin_user,
                'description': 'Grid template for the reference image puzzle',
                'difficulty': 'easy',
                'grid_data': [
                    [green_circle.id, None, None],
                    [None, '?', None],
                    [blue_triangle.id, None, green_circle.id]
                ]
            }
        )

        # Create shape game
        shape_game, created = ShapeGame.objects.get_or_create(
            name='Reference Image Puzzle',
            defaults={
                'grid_template': grid_template,
                'created_by': admin_user,
                'description': 'A 3x3 puzzle matching the reference image with green circles, blue triangle, and question mark.',
                'is_active': True,
                'solution_data': {
                    'grid': [
                        [green_circle.id, None, None],
                        [None, red_square.id, None],  # The answer is red square in the center
                        [blue_triangle.id, None, green_circle.id]
                    ],
                    'answer_position': {'row': 1, 'col': 1},
                    'correct_answer': red_square.id
                },
                'max_time_minutes': 10,
                'points_per_correct': 100,
                'penalty_per_wrong': 10
            }
        )
        
        # Add available shapes to the game
        if created:
            shape_game.available_shapes.set([green_circle, blue_triangle, red_square])

        # Create or get puzzle level
        puzzle_level, created = PuzzleLevel.objects.get_or_create(
            level_number=1,
            defaults={
                'name': 'Reference Puzzle Level',
                'description': 'Level containing the reference image puzzle',
                'required_score': 0,
                'unlock_condition': 'always',
                'created_by': admin_user
            }
        )

        # Create level puzzle
        level_puzzle, created = LevelPuzzle.objects.get_or_create(
            level=puzzle_level,
            shape_game=shape_game,
            defaults={
                'order_in_level': 1,
                'points_reward': 100
            }
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Reference puzzle created successfully!\n'
                f'Shape Game: {shape_game.name}\n'
                f'Grid Template: {grid_template.name}\n'
                f'Puzzle Level: {puzzle_level.name}\n'
                f'Shapes used: {green_circle.name}, {blue_triangle.name}, {red_square.name}\n'
                f'Answer position: Row 1, Column 1 (center)\n'
                f'Correct answer: {red_square.name}'
            )
        )

        # Display the grid layout
        self.stdout.write('\nPuzzle Grid Layout:')
        grid_data = grid_template.grid_data
        for i, row in enumerate(grid_data):
            row_display = []
            for j, cell in enumerate(row):
                if cell == '?':
                    row_display.append('?')
                elif cell:
                    shape = Shape.objects.get(id=cell)
                    if 'green' in shape.name.lower():
                        row_display.append('G')
                    elif 'blue' in shape.name.lower():
                        row_display.append('B')
                    elif 'red' in shape.name.lower():
                        row_display.append('R')
                    else:
                        row_display.append('S')
                else:
                    row_display.append('.')
            self.stdout.write(f'  {" ".join(row_display)}')
        
        self.stdout.write('\nShape Options:')
        self.stdout.write(f'  - {green_circle.name}')
        self.stdout.write(f'  - {blue_triangle.name}')
        self.stdout.write(f'  - {red_square.name}')