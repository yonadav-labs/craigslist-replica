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

