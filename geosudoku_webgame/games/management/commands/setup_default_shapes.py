from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from games.models import Shape, ShapeType

User = get_user_model()

class Command(BaseCommand):
    help = 'Create default shapes for the shape puzzle system'

    def handle(self, *args, **options):
        # Get or create admin user
        admin_user = User.objects.filter(role='ADMIN').first()
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.WARNING('No admin user found. Creating default admin.'))
            admin_user = User.objects.create_user(
                username='admin',
                email='admin@example.com',
                password='admin123',
                role='ADMIN',
                is_superuser=True
            )

        # Default shapes for the puzzle system
        default_shapes = [
            {
                'name': 'Red Circle',
                'shape_type': ShapeType.CIRCLE,
                'color': '#dc3545',
                'svg_data': '<circle cx="20" cy="20" r="16" fill="currentColor"/>'
            },
            {
                'name': 'Blue Square',
                'shape_type': ShapeType.SQUARE,
                'color': '#007bff',
                'svg_data': '<rect x="4" y="4" width="32" height="32" fill="currentColor"/>'
            },
            {
                'name': 'Green Triangle',
                'shape_type': ShapeType.TRIANGLE,
                'color': '#28a745',
                'svg_data': '<polygon points="20,4 36,36 4,36" fill="currentColor"/>'
            },
            {
                'name': 'Orange Diamond',
                'shape_type': ShapeType.DIAMOND,
                'color': '#fd7e14',
                'svg_data': '<polygon points="20,4 36,20 20,36 4,20" fill="currentColor"/>'
            },
            {
                'name': 'Purple Star',
                'shape_type': ShapeType.STAR,
                'color': '#6f42c1',
                'svg_data': '<polygon points="20,2 24,14 36,14 27,22 31,34 20,28 9,34 13,22 4,14 16,14" fill="currentColor"/>'
            },
            {
                'name': 'Teal Hexagon',
                'shape_type': ShapeType.HEXAGON,
                'color': '#20c997',
                'svg_data': '<polygon points="30,8 38,20 30,32 10,32 2,20 10,8" fill="currentColor"/>'
            }
        ]

        created_count = 0
        updated_count = 0

        for shape_data in default_shapes:
            shape, created = Shape.objects.get_or_create(
                name=shape_data['name'],
                defaults={
                    'shape_type': shape_data['shape_type'],
                    'color': shape_data['color'],
                    'svg_data': shape_data['svg_data'],
                    'created_by': admin_user,
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created shape: {shape.name}')
                )
            else:
                # Update existing shape if needed
                shape.color = shape_data['color']
                shape.svg_data = shape_data['svg_data']
                shape.is_active = True
                shape.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated shape: {shape.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDefault shapes setup complete!\n'
                f'Created: {created_count} shapes\n'
                f'Updated: {updated_count} shapes\n'
                f'Total shapes available: {Shape.objects.filter(is_active=True).count()}'
            )
        )

        # Display available shapes
        self.stdout.write('\nAvailable shapes:')
        for shape in Shape.objects.filter(is_active=True).order_by('id'):
            self.stdout.write(f'  - {shape.name} ({shape.shape_type}) - {shape.color}')