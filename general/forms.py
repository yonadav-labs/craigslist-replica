from django import forms
from django.forms import ModelForm
from django.forms.utils import ErrorList

from .models import *

class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = '__all__'


class JobPostForm(ModelForm):
    class Meta:
        model = JobPost
        fields = '__all__'


class GaragePostForm(ModelForm):
    class Meta:
        model = GaragePost
        fields = '__all__'


class SaleGarageForm(ModelForm):
    class Meta:
        model = SaleGarage
        fields = '__all__'

class CustomerForm(ModelForm):
    # dob = forms.DateTimeField(input_formats='%d-%m-%Y')

    class Meta:
        model = Customer
        exclude = ['password', 'date_joined', 'last_login', 'is_superuser', 
                   'is_staff', 'is_active', 'phone_verified', 'forum_handle',
                   'default_site', 'duration']
