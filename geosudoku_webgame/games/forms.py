from django import forms
from django.core.exceptions import ValidationError
import json
from .models import Shape, GridTemplate, ShapeGame, ShapeType, DifficultyLevel


class ShapeUploadForm(forms.ModelForm):
    """
    Form for uploading and managing shapes by admins
    """
    class Meta:
        model = Shape
        fields = ['name', 'shape_type', 'color', 'svg_data', 'image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter shape name (e.g., "Red Triangle")'
            }),
            'shape_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'Choose color'
            }),
            'svg_data': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Enter SVG path data or complete SVG element...'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
    
    def clean_svg_data(self):
        """Validate SVG data"""
        svg_data = self.cleaned_data.get('svg_data')
        if svg_data:
            # Basic SVG validation
            svg_data = svg_data.strip()
            if not (svg_data.startswith('<svg') or svg_data.startswith('<path')):
                # If it's just path data, wrap it in an SVG element
                if not svg_data.startswith('M') and not svg_data.startswith('m'):
                    raise ValidationError("SVG data must be valid SVG markup or path data starting with 'M' or 'm'")
                # Wrap path data in SVG element
                svg_data = f'<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><path d="{svg_data}" fill="currentColor"/></svg>'
            
            # Check for basic SVG structure
            if '<svg' not in svg_data.lower():
                raise ValidationError("Invalid SVG format. Must contain <svg> element.")
                
        return svg_data
    
    def clean_name(self):
        """Validate shape name"""
        name = self.cleaned_data.get('name')
        if name:
            # Check for duplicate names within the same shape type
            shape_type = self.cleaned_data.get('shape_type')
            if shape_type:
                existing = Shape.objects.filter(
                    name__iexact=name, 
                    shape_type=shape_type
                ).exclude(pk=self.instance.pk if self.instance.pk else None)
                if existing.exists():
                    raise ValidationError(f"A {shape_type} shape with this name already exists.")
        return name


class GridTemplateForm(forms.ModelForm):
    """
    Form for creating and managing grid templates
    """
    class Meta:
        model = GridTemplate
        fields = ['name', 'description', 'grid_size', 'grid_data', 'difficulty']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter template name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this template...'
            }),
            'grid_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '3',
                'max': '15',
                'value': '9'
            }),
            'grid_data': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Enter grid data as JSON array...'
            }),
            'difficulty': forms.Select(attrs={
                'class': 'form-select'
            })
        }
    
    def clean_grid_data(self):
        """Validate grid data JSON format"""
        grid_data = self.cleaned_data.get('grid_data')
        grid_size = self.cleaned_data.get('grid_size', 9)
        
        if grid_data:
            try:
                # Parse JSON
                grid = json.loads(grid_data) if isinstance(grid_data, str) else grid_data
                
                # Validate structure
                if not isinstance(grid, list):
                    raise ValidationError("Grid data must be a JSON array.")
                
                if len(grid) != grid_size:
                    raise ValidationError(f"Grid must have exactly {grid_size} rows.")
                
                for i, row in enumerate(grid):
                    if not isinstance(row, list):
                        raise ValidationError(f"Row {i+1} must be an array.")
                    if len(row) != grid_size:
                        raise ValidationError(f"Row {i+1} must have exactly {grid_size} columns.")
                    
                    # Validate cell values
                    for j, cell in enumerate(row):
                        if cell not in ['?', 0, '0', None, '']:
                            # Allow shape IDs or references
                            if not isinstance(cell, (str, int)):
                                raise ValidationError(f"Invalid cell value at row {i+1}, column {j+1}. Use '?' for question cells, 0 for empty, or shape references.")
                
                # Count question mark cells
                question_count = sum(1 for row in grid for cell in row if cell == '?')
                if question_count == 0:
                    raise ValidationError("Grid must contain at least one question mark cell ('?').")
                
                return grid
                
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON format: {e}")
            except Exception as e:
                raise ValidationError(f"Grid validation error: {e}")
        
        return grid_data
    
    def clean_grid_size(self):
        """Validate grid size"""
        grid_size = self.cleaned_data.get('grid_size')
        if grid_size and (grid_size < 3 or grid_size > 15):
            raise ValidationError("Grid size must be between 3 and 15.")
        return grid_size


class ShapeGameForm(forms.ModelForm):
    """
    Form for creating shape-based games
    """
    class Meta:
        model = ShapeGame
        fields = [
            'name', 'description', 'grid_template', 'available_shapes',
            'solution_data', 'max_time_minutes', 'points_per_correct', 'penalty_per_wrong'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter game name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this game...'
            }),
            'grid_template': forms.Select(attrs={
                'class': 'form-select'
            }),
            'available_shapes': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
            'solution_data': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Enter solution mapping as JSON...'
            }),
            'max_time_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '5',
                'max': '120',
                'value': '30'
            }),
            'points_per_correct': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '100',
                'value': '10'
            }),
            'penalty_per_wrong': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '50',
                'value': '5'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active templates and shapes
        self.fields['grid_template'].queryset = GridTemplate.objects.filter(is_active=True)
        self.fields['available_shapes'].queryset = Shape.objects.filter(is_active=True)
    
    def clean_solution_data(self):
        """Validate solution data format"""
        solution_data = self.cleaned_data.get('solution_data')
        grid_template = self.cleaned_data.get('grid_template')
        
        if solution_data and grid_template:
            try:
                solution = json.loads(solution_data) if isinstance(solution_data, str) else solution_data
                
                if not isinstance(solution, dict):
                    raise ValidationError("Solution data must be a JSON object.")
                
                # Validate that solution covers all question mark cells
                grid_data = grid_template.grid_data
                question_cells = []
                for i, row in enumerate(grid_data):
                    for j, cell in enumerate(row):
                        if cell == '?':
                            question_cells.append(f"{i},{j}")
                
                # Check if all question cells have solutions
                missing_cells = [cell for cell in question_cells if cell not in solution]
                if missing_cells:
                    raise ValidationError(f"Solution missing for cells: {missing_cells}")
                
                return solution
                
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON format: {e}")
            except Exception as e:
                raise ValidationError(f"Solution validation error: {e}")
        
        return solution_data
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        grid_template = cleaned_data.get('grid_template')
        available_shapes = cleaned_data.get('available_shapes')
        solution_data = cleaned_data.get('solution_data')
        
        if grid_template and available_shapes and solution_data:
            try:
                solution = json.loads(solution_data) if isinstance(solution_data, str) else solution_data
                shape_ids = [shape.id for shape in available_shapes]
                
                # Check if all shapes in solution are available
                for cell, shape_id in solution.items():
                    if shape_id not in shape_ids:
                        raise ValidationError(f"Shape ID {shape_id} in solution is not in available shapes.")
                        
            except (json.JSONDecodeError, TypeError):
                pass  # Already handled in clean_solution_data
        
        return cleaned_data


class GridTemplateBuilderForm(forms.Form):
    """
    Interactive form for building grid templates with visual editor
    """
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Template Name'
        })
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Description (optional)'
        })
    )
    
    grid_size = forms.IntegerField(
        min_value=4,
        max_value=5,
        initial=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'grid-size-input'
        })
    )
    
    difficulty = forms.ChoiceField(
        choices=DifficultyLevel.choices,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    # Hidden field to store grid data with answers
    grid_data = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    def clean_grid_data(self):
        """Validate grid data with answer information"""
        grid_data = self.cleaned_data.get('grid_data')
        if grid_data:
            try:
                data = json.loads(grid_data)
                
                # Validate structure
                if not isinstance(data, dict):
                    raise ValidationError("Grid data must be a JSON object.")
                
                required_keys = ['grid_data', 'solution_data', 'answer_data']
                for key in required_keys:
                    if key not in data:
                        raise ValidationError(f"Missing required field: {key}")
                
                grid = data['grid_data']
                solution = data['solution_data']
                answers = data['answer_data']
                
                # Validate grid structure
                grid_size = self.cleaned_data.get('grid_size', 5)
                if len(grid) != grid_size or any(len(row) != grid_size for row in grid):
                    raise ValidationError(f"Grid must be {grid_size}x{grid_size}.")
                
                # Count question marks and validate answers
                question_count = 0
                for i, row in enumerate(grid):
                    for j, cell in enumerate(row):
                        if cell == '?':
                            question_count += 1
                            cell_key = f"{i}-{j}"
                            if cell_key not in answers:
                                raise ValidationError(f"Missing answer for question cell at position ({i}, {j})")
                
                if question_count == 0:
                    raise ValidationError("Grid must have at least one question cell.")
                
                return data
                
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON: {e}")
        
        return grid_data