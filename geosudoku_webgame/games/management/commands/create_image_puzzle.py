from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from games.models import Shape, GridTemplate, ShapeGame, PuzzleLevel, LevelPuzzle
import json

User = get_user_model()

class Command(BaseCommand):
    help = 'Create the puzzle from the uploaded image'

    def handle(self, *args, **options):
        # Get or create admin user
        admin_user = User.objects.filter(role='ADMIN').first()
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True).first()
        
        if not admin_user:
            self.stdout.write(self.style.ERROR('No admin user found. Please create an admin user first.'))
            return

        # Create shapes if they don't exist
        shapes_data = [
            {
                'name': 'Green Circle',
                'shape_type': 'circle',
                'color': '#7CB342',  # Green color from image
                'svg_data': '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="40" fill="currentColor" stroke="#000" stroke-width="2"/>
</svg>'''
            },
            {
                'name': 'Blue Triangle',
                'shape_type': 'triangle',
                'color': '#1976D2',  # Blue color from image
                'svg_data': '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <polygon points="50,15 85,85 15,85" fill="currentColor" stroke="#000" stroke-width="2"/>
</svg>'''
            },
            {
                'name': 'Red Square',
                'shape_type': 'square',
                'color': '#D32F2F',  # Red color from image
                'svg_data': '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <rect x="15" y="15" width="70" height="70" fill="currentColor" stroke="#000" stroke-width="2"/>
</svg>'''
            }
        ]

        created_shapes = []
        for shape_data in shapes_data:
            shape, created = Shape.objects.get_or_create(
                name=shape_data['name'],
                defaults={
                    'shape_type': shape_data['shape_type'],
                    'color': shape_data['color'],
                    'svg_data': shape_data['svg_data'],
                    'created_by': admin_user
                }
            )
            created_shapes.append(shape)
            if created:
                self.stdout.write(f'Created shape: {shape.name}')
            else:
                self.stdout.write(f'Shape already exists: {shape.name}')

        # Create 3x3 grid template for the puzzle
        # Based on the image: Row 1: Green circle(1), empty, empty
        #                     Row 2: empty, question mark(?), empty  
        #                     Row 3: Blue triangle(2), empty, Green circle(1)
        grid_data = [
            [1, '?', '?'],  # Green circle, empty, empty
            ['?', '?', '?'],  # Empty, question mark (will be shown as ?), empty
            [2, '?', 1]   # Blue triangle, empty, green circle
        ]

        template, created = GridTemplate.objects.get_or_create(
            name="3x3 Shape Pattern Puzzle",
            defaults={
                'description': 'A 3x3 grid puzzle based on the uploaded image pattern',
                'grid_size': 3,
                'difficulty': 'medium',
                'grid_data': grid_data,
                'created_by': admin_user
            }
        )

        if created:
            self.stdout.write(f'Created template: {template.name}')
        else:
            self.stdout.write(f'Template already exists: {template.name}')

        # Create the puzzle (ShapeGame)
        puzzle, created = ShapeGame.objects.get_or_create(
            name="Image Pattern Puzzle",
            defaults={
                'description': '''Complete the 3x3 grid pattern! 
                
Looking at the pattern:
- Row 1: Green circle in position 1
- Row 3: Blue triangle in position 1, Green circle in position 3

Can you figure out what goes in the middle cell (marked with ?) and complete the rest of the grid?

Available shapes: Green Circle, Blue Triangle, Red Square''',
                'grid_template': template,
                'max_time_minutes': 5,
                'points_per_correct': 10,
                'penalty_per_wrong': 5,
                'created_by': admin_user,
                'solution_data': {
                    'grid': [
                        [1, 3, 2],  # Green circle, Red square, Blue triangle
                        [2, 1, 3],  # Blue triangle, Green circle, Red square  
                        [2, 3, 1]   # Blue triangle, Red square, Green circle
                    ],
                    'explanation': 'Each row and column must contain each shape exactly once - like a Sudoku with shapes!'
                }
            }
        )

        if created:
            self.stdout.write(f'Created puzzle: {puzzle.name}')
            
            # Add shapes to the puzzle
            for shape in created_shapes:
                puzzle.available_shapes.add(shape)
            
            # Create or get a level for this puzzle
            level, level_created = PuzzleLevel.objects.get_or_create(
                level_number=1,
                defaults={
                    'name': 'Beginner Shape Patterns',
                    'description': 'Learn basic shape pattern recognition',
                    'unlock_level': 0,
                    'created_by': admin_user
                }
            )
            
            if level_created:
                self.stdout.write(f'Created level: {level.name}')
            
            # Add puzzle to level
            level_puzzle, lp_created = LevelPuzzle.objects.get_or_create(
                level=level,
                shape_game=puzzle,
                defaults={
                    'order_in_level': 1,
                    'points_reward': 100
                }
            )
            
            if lp_created:
                self.stdout.write(f'Added puzzle to level: {level.name}')
                
        else:
            self.stdout.write(f'Puzzle already exists: {puzzle.name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Successfully created puzzle system based on your image!\n'
                f'🎯 Puzzle: "{puzzle.name}"\n'
                f'🔤 Shapes: {", ".join([s.name for s in created_shapes])}\n'
                f'📊 Level: "{level.name}"\n'
                f'🎮 You can now play this puzzle in the game!'
            )
        )