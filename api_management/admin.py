from django.contrib import admin
from .models import API, Endpoint, Method, Parameter, Header, APILog, APICallQuota , OAuthConfig
from django import forms




class APIAdminForm(forms.ModelForm):
    class Meta:
        model = API
        fields = '__all__'

        
@admin.register(API)
class APIAdmin(admin.ModelAdmin):
    form = APIAdminForm
    list_display = ('id','name', 'url', 'auth_required')
    search_fields = ('name', 'url')

    def has_add_permission(self, request):
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Endpoint)
class EndpointAdmin(admin.ModelAdmin):
    list_display = ('id','api', 'path', 'user_input_required')
    list_filter = ('api',)
    search_fields = ('path', 'description')

@admin.register(Method)
class MethodAdmin(admin.ModelAdmin):
    list_display = ('endpoint', 'method', 'return_code')
    list_filter = ('endpoint__api', 'method')
    search_fields = ('endpoint__path',)

@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = (
        'endpoint',
        'name',
        'param_type',
        'data_type',
        'required',
        'editable'
    )
    exclude = ('stored_value','default_value')
    list_filter = ('endpoint__api', 'param_type', 'data_type')
    search_fields = ('name', 'description')

@admin.register(Header)
class HeaderAdmin(admin.ModelAdmin):
    list_display = ('endpoint', 'name')
    exclude = ('value',)
    list_filter = ('endpoint__api',)
    search_fields = ('name',)

@admin.register(APILog)
class APILogAdmin(admin.ModelAdmin):
    list_display = ('user', 'api', 'endpoint', 'method', 'status_code', 'timestamp')
    list_filter = ('api', 'endpoint', 'method', 'status_code')
    search_fields = ('user__username', 'api__name', 'endpoint__path')

@admin.register(APICallQuota)
class APICallQuotaAdmin(admin.ModelAdmin):
    list_display = ('user', 'month', 'year', 'call_count', 'monthly_limit')
    list_filter = ('month', 'year')
    search_fields = ('user__username',)
    list_editable = ('monthly_limit',)
    
@admin.register(OAuthConfig)
class OAuthConfigAdmin(admin.ModelAdmin):
    list_display = ('api', 'grant_type', 'token_url')
    list_filter = ('grant_type',)
    search_fields = ('api__name', 'token_url')