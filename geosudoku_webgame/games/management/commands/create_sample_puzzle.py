from django.core.management.base import BaseCommand
from games.models import Shape, ShapeGame, GridTemplate
from authentication.models import User
import json

class Command(BaseCommand):
    help = 'Create a sample 3x3 puzzle for testing'

    def handle(self, *args, **options):
        # Get admin user
        admin_user = User.objects.filter(is_staff=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR('No admin user found. Run create_distinct_shapes first.'))
            return
        
        # Get shapes
        shapes = list(Shape.objects.all()[:3])  # Get first 3 shapes for 3x3 grid
        if len(shapes) < 3:
            self.stdout.write(self.style.ERROR('Not enough shapes found. Run create_distinct_shapes first.'))
            return
        
        # Create sample 3x3 puzzle layout
        # Layout: 
        # [Circle] [    ] [Square]
        # [    ] [?] [    ]
        # [Star] [    ] [    ]
        
        grid_data = {}
        
        # Place shapes
        grid_data["0"] = {"0": {"type": "shape", "shapeId": shapes[0].id, "shapeName": shapes[0].name}}  # Circle at (0,0)
        grid_data["0"]["2"] = {"type": "shape", "shapeId": shapes[1].id, "shapeName": shapes[1].name}  # Square at (0,2)
        grid_data["1"] = {"1": {"type": "question", "display": "?"}}  # Question mark at (1,1)
        grid_data["2"] = {"0": {"type": "shape", "shapeId": shapes[2].id, "shapeName": shapes[2].name}}  # Star at (2,0)
        
        # Create GridTemplate first
        grid_template = GridTemplate.objects.create(
            name="Sample 3x3 Template",
            description="A 3x3 grid template for sample puzzle",
            grid_size=3,
            grid_data=grid_data,
            difficulty='easy',
            created_by=admin_user
        )
        
        # Create solution data (where question marks should be answered)
        solution_data = {
            "1": {"1": {"type": "shape", "shapeId": shapes[0].id, "shapeName": shapes[0].name}}  # Circle can be answer
        }
        
        # Create the shape game
        sample_game = ShapeGame.objects.create(
            name="Sample 3x3 Puzzle",
            description="A sample puzzle with circle, square, star and one question mark. Perfect for testing!",
            grid_template=grid_template,
            solution_data=solution_data,
            max_time_minutes=5,  # 5 minutes
            points_per_correct=20,
            penalty_per_wrong=5,
            created_by=admin_user
        )
        
        # Add shapes to the game
        sample_game.available_shapes.set(shapes[:3])
        
        self.stdout.write(
            self.style.SUCCESS(f'Created grid template: {grid_template.name}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Created sample puzzle: {sample_game.name}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Puzzle ID: {sample_game.id}')
        )
        self.stdout.write(
            self.style.SUCCESS('Layout:')
        )
        self.stdout.write(f'  [{shapes[0].name}] [    ] [{shapes[1].name}]')
        self.stdout.write(f'  [    ] [ ? ] [    ]')
        self.stdout.write(f'  [{shapes[2].name}] [    ] [    ]')
        self.stdout.write(
            self.style.SUCCESS('Sample puzzle created successfully!')
        )