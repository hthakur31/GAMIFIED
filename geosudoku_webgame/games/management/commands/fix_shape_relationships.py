from django.core.management.base import BaseCommand
from games.models import ShapeGame, Shape

class Command(BaseCommand):
    help = 'Fix shape relationships for all games to ensure consistency'

    def handle(self, *args, **options):
        self.stdout.write('🔧 Fixing Shape Relationships...')
        
        # Get all shape games
        games = ShapeGame.objects.filter(is_active=True)
        
        for game in games:
            self.stdout.write(f'\n🎮 Processing Game: {game.name}')
            
            # Get all shape IDs used in this game
            used_shape_ids = set()
            grid_data = game.grid_template.grid_data
            solution_data = game.solution_data
            
            # Extract shape IDs from grid data
            if isinstance(grid_data, dict):
                # Object-based structure
                for row_key, row_data in grid_data.items():
                    if isinstance(row_data, dict):
                        for col_key, cell_data in row_data.items():
                            if cell_data and isinstance(cell_data, dict) and cell_data.get('type') == 'shape':
                                used_shape_ids.add(cell_data.get('shapeId'))
            elif isinstance(grid_data, list):
                # List-based structure
                for row_idx, row_data in enumerate(grid_data):
                    if isinstance(row_data, list):
                        for col_idx, cell_data in enumerate(row_data):
                            if cell_data and isinstance(cell_data, dict) and cell_data.get('type') == 'shape':
                                used_shape_ids.add(cell_data.get('shapeId'))
            
            # Extract shape IDs from solution data
            if isinstance(solution_data, dict):
                for row_key, row_data in solution_data.items():
                    if isinstance(row_data, dict):
                        for col_key, cell_data in row_data.items():
                            if cell_data and isinstance(cell_data, dict) and cell_data.get('type') == 'shape':
                                used_shape_ids.add(cell_data.get('shapeId'))
            elif isinstance(solution_data, list):
                for row_idx, row_data in enumerate(solution_data):
                    if isinstance(row_data, list):
                        for col_idx, cell_data in enumerate(row_data):
                            if cell_data and isinstance(cell_data, dict) and cell_data.get('type') == 'shape':
                                used_shape_ids.add(cell_data.get('shapeId'))
            
            # Remove None values
            used_shape_ids.discard(None)
            
            self.stdout.write(f'   Used Shape IDs: {used_shape_ids}')
            
            # Get actual Shape objects
            shapes_to_add = Shape.objects.filter(id__in=used_shape_ids, is_active=True)
            
            # Clear existing relationships and add correct ones
            game.available_shapes.clear()
            for shape in shapes_to_add:
                game.available_shapes.add(shape)
                self.stdout.write(f'   ✅ Added shape: {shape.name} (ID: {shape.id})')
            
            game.save()
        
        self.stdout.write('\n🎉 Shape relationships fixed successfully!')