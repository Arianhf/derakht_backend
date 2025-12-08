from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Address


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    fields = ('recipient_name', 'city', 'province', 'postal_code', 'phone_number', 'is_default')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [AddressInline]
    list_display = (
        'email',
        'username',
        'first_name',
        'last_name',
        'age',
        'is_verified',
        'is_staff',
        'is_active',
        'date_joined',
    )
    list_filter = (
        'is_staff',
        'is_active',
        'is_verified',
        'is_superuser',
        'date_joined',
    )
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')

    fieldsets = (
        (None, {
            'fields': ('email', 'username', 'password')
        }),
        (_('Personal Info'), {
            'fields': ('first_name', 'last_name', 'age', 'phone_number', 'profile_image')
        }),
        (_('Author/SEO Info'), {
            'fields': ('bio', 'social_links'),
            'classes': ('collapse',)
        }),
        (_('Verification'), {
            'fields': ('is_verified', 'email_verification_token')
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'date_joined')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'first_name', 'last_name', 'age'),
        }),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        'recipient_name',
        'user',
        'city',
        'province',
        'postal_code',
        'is_default',
        'created_at',
    )
    list_filter = ('is_default', 'province', 'city', 'created_at')
    search_fields = ('recipient_name', 'address', 'city', 'province', 'postal_code', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-is_default', '-created_at')

    fieldsets = (
        (_('Address Information'), {
            'fields': ('user', 'recipient_name', 'phone_number')
        }),
        (_('Location'), {
            'fields': ('address', 'city', 'province', 'postal_code')
        }),
        (_('Settings'), {
            'fields': ('is_default',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
