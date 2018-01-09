import datetime

from django import template
from django.db.models import Avg

from general.models import *

register = template.Library()

@register.filter
def raised_percent(campaign, css=False):
    percent = campaign.raised * 100 / campaign.budget
    if css and percent > 100:
        percent = 100
    return percent

@register.filter
def ramained_days(campaign):
    return (campaign.created_at + datetime.timedelta(days=campaign.duration) - datetime.datetime.now().date()).days
    
@register.filter
def get_vids(campaign):
    vids = [ii.strip() for ii in campaign.videos.split(',') if ii.strip()]
    return vids

@register.filter
def rating(customer):
    rate = Review.objects.filter(post__owner=customer).aggregate(Avg('rating')).values()[0]
    return rate if rate else 0

@register.filter
def rating_post(post):
    rate = Review.objects.filter(post=post).aggregate(Avg('rating')).values()[0]
    return rate if rate else 0

@register.filter
def rangee(start, end):
	return range(start, end)
