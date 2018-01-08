# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.dispatch import receiver
from django.db.models.signals import pre_delete
from django.db.models.signals import post_save
from django.conf import settings

from general.models import *
from general.post_models import *

from general.utils import send_email


@receiver(pre_delete, sender=Image, dispatch_uid='image_delete_signal')
def delete_image_file(sender, instance, using, **kwargs):
    try:
        os.remove(settings.BASE_DIR+'/static/media/'+instance.name)
    except Exception, e:
        print e, '@@@@@ Error in delete_image_file()'

@receiver(post_save, sender=Post)
@receiver(post_save, sender=JobPost)
@receiver(post_save, sender=GaragePost)
@receiver(post_save, sender=SaleGarage)
def apply_subscribe(sender, instance, **kwargs):    
    try:
        for ss in Search.objects.filter(alert=True).exclude(owner=instance.owner):
            if not ss.keyword or ss.keyword.lower() in instance.title.lower() or ss.keyword.lower() in instance.content.lower():
                if ss.city == instance.region or ss.state == instance.region.state:
                    if ss.category == instance.category or ss.category == instance.category.parent:
                        subscription_info = ''

                        content = """
                            1 new result for your subscription ( {1} ) as of {2}<br><br>
                            <a href="http://{0}/ads/{3}">{4}</a><br><br>
                            <a href="http://{0}/my-subscribe">Review all saved searches.</a><br><br>
                            Thank you for using <a href="http://{0}/">Globalboard</a>.                         
                        """.format(settings.ALLOWED_HOSTS[0], ss.category.name, str(instance.created_at), instance.id, instance.title)
                        send_email(settings.FROM_EMAIL, 'Globalboard Subscription Alarm', ss.owner.email, content)
    except Exception, e:
        print e, '@@@@@ Error in apply_subscribe()'

@receiver(post_save, sender=Review)
def rating_notify(sender, instance, **kwargs):    
    try:
        content = '<a href="http://{0}/user/{}">{} {}</a> left review on your ads ({}) at {}'.format(settings.ALLOWED_HOSTS[0], instance.rater.id, instance.rater.first_name,
            instance.rater.last_name, instance.post.title, instance.created_at)
        send_email(settings.FROM_EMAIL, 'Globalboard Rating Notification', instance.post.owner.email, content)
    except Exception, e:
        print e, '@@@@@ Error in rating_notify()'

@receiver(post_save, sender=PostPurchase)
def post_purchase_notify(sender, instance, **kwargs):    
    try:
        # send email to the owner
        content = "Ads (<a href='http://{0}/ads/{1}'>{2}</a>) is purchased by {3} {4} at {5}<br><br>Contact Info:<br>" \
                  .format(settings.ALLOWED_HOSTS[0], instance.post.id, instance.post.title, 
                          instance.purchaser.first_name, instance.purchaser.last_name, instance.created_at)
        if instance.type == 'direct':
            subject = 'Item purchased directly'
        else:
            subject = 'Item purchased via escrow'

        content += instance.contact
        send_email(settings.FROM_EMAIL, subject, instance.post.owner.email, content)

    except Exception, e:
        print e, '@@@@@ Error in post_purchase_notify()'
