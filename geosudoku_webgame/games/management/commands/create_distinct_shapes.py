from django.core.management.base import BaseCommand
from games.models import Shape
from authentication.models import User

class Command(BaseCommand):
    help = 'Create distinct shapes: circle, square, star, triangle, plus'

    def handle(self, *args, **options):
        # Get or create admin user
        admin_user = User.objects.filter(is_staff=True).first()
        if not admin_user:
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
        
        # Clear existing shapes
        Shape.objects.all().delete()
        
        # Define distinct shapes with clear SVG definitions
        shapes_data = [
            {
                'name': 'Green Circle',
                'shape_type': 'circle',
                'color': '#28a745',  # Green
                'svg_data': '<circle cx="20" cy="20" r="15" fill="currentColor"/>',
                'created_by': admin_user
            },
            {
                'name': 'Blue Square',
                'shape_type': 'square', 
                'color': '#007bff',  # Blue
                'svg_data': '<rect x="5" y="5" width="30" height="30" fill="currentColor"/>',
                'created_by': admin_user
            },
            {
                'name': 'Red Star',
                'shape_type': 'star',
                'color': '#dc3545',  # Red
                'svg_data': '<polygon points="20,5 25,15 35,15 27,23 30,33 20,27 10,33 13,23 5,15 15,15" fill="currentColor"/>',
                'created_by': admin_user
            },
            {
                'name': 'Purple Triangle',
                'shape_type': 'triangle',
                'color': '#6f42c1',  # Purple
                'svg_data': '<polygon points="20,5 35,30 5,30" fill="currentColor"/>',
                'created_by': admin_user
            },
            {
                'name': 'Orange Plus',
                'shape_type': 'plus',
                'color': '#fd7e14',  # Orange
                'svg_data': '<rect x="16" y="8" width="8" height="24" fill="currentColor"/><rect x="8" y="16" width="24" height="8" fill="currentColor"/>',
                'created_by': admin_user
            }
        ]
        
        for shape_data in shapes_data:
            shape = Shape.objects.create(**shape_data)
            self.stdout.write(
                self.style.SUCCESS(f'Created shape: {shape.name}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {len(shapes_data)} distinct shapes!')
        )