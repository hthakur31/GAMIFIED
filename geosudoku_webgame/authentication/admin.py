from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'total_score', 'games_played', 'win_rate', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Permissions', {
            'fields': ('role',)
        }),
        ('Game Statistics', {
            'fields': ('total_score', 'games_played', 'games_won', 'bio', 'avatar')
        }),
    )
    
    readonly_fields = ('win_rate',)
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        # Show role field for superusers and game admins
        if not request.user.is_superuser and not (hasattr(request.user, 'is_game_admin') and request.user.is_game_admin):
            # Remove role fieldset for regular users
            fieldsets = [fs for fs in fieldsets if fs[0] != 'Role & Permissions']
        return fieldsets
