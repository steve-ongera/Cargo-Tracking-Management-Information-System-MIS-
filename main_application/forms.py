# forms.py
from django import forms
from .models import CargoCategory, County


class CargoCategoryForm(forms.ModelForm):
    class Meta:
        model = CargoCategory
        fields = ['name', 'code', 'description', 'requires_special_handling', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter category name'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., ELEC, FOOD, MACH'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': 'Category description (optional)'
            }),
            'requires_special_handling': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
        }
        help_texts = {
            'code': 'Unique code for this category (max 10 characters)',
            'requires_special_handling': 'Check if this category requires special handling',
        }


class CountyForm(forms.ModelForm):
    class Meta:
        model = County
        fields = ['name', 'code']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter county name'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., 001, 047',
                'maxlength': '3'
            }),
        }
        help_texts = {
            'code': '3-digit county code',
        }