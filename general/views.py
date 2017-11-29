# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import json
import stripe

from random import randint

from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.template.loader import render_to_string
from django.db.models import Q

from general.models import *
from general.forms import *
from general.utils import send_email, send_SMS

get_class = lambda x: globals()[x]
stripe.api_key = settings.STRIPE_KEYS['API_KEY']

def home(request):
    rndr_str = globoard_display_world_countries()
    return render(request, 'index.html', {'rndr_str': rndr_str})

@login_required(login_url='/accounts/login')
def my_ads(request):
    posts = Post.objects.filter(owner=request.user)
    posts = get_posts_with_image(posts)
    return render(request, 'my-ads.html', {'posts': posts})

@csrf_exempt
def search_ads(request):
    keyword = request.POST.get('keyword')
    others = request.POST.get('others')

    if others:
        region_id = request.session['region']  # city
        region_kind = request.session['region_kind']
        category_id = request.session['category']

        if region_kind == 'state':
            posts = Post.objects.filter(region__state__id=region_id)
        elif region_kind == 'city':
            posts = Post.objects.filter(region_id=region_id)

        if category_id:
            categories = Category.objects.filter(Q(id=category_id) | Q(parent__id=category_id))
            posts = posts.filter(category__in=categories)

        posts = posts.filter(Q(title__icontains=keyword) | Q(content__icontains=keyword)) \
                     .exclude(status='deactive')
    else:
        posts = Post.objects.filter(owner=request.user).filter(Q(title__icontains=keyword) | Q(content__icontains=keyword))

    posts = get_posts_with_image(posts)
    rndr_str = render_to_string('_post_list.html', {'posts': posts, 'others': others})
    return HttpResponse(rndr_str)

def get_posts_with_image(posts):
    posts_with_image = []
    for post in posts:
        image = Image.objects.filter(post=post).first()
        img_name = image.name if image else 'dummy.jpg'
        posts_with_image.append((post, img_name))
    return posts_with_image

def profile(request):
    return render(request, 'profile.html')

def breadcrumb(request):
    mapName = request.GET.get('mapName')
    state = request.GET.get('state').replace('%27', "'") \
                                    .replace('%20', " ")
    is_state = request.GET.get('is_state')
    city = request.GET.get('city')
    kind = mapName.count('-')

    html = '<a class="breadcrumb-item" href="javascript:void();" data-mapname="custom/world">worldwide</a>'

    if city:
        city = City.objects.get(id=city)
        mapname = 'countries/{0}/{0}-all'.format(city.state.country.sortname.lower())
        html += """
            <a class="breadcrumb-item country-brcm" href="javascript:void();" data-mapname="{}">
                <i class="fa fa-long-arrow-right" aria-hidden="true"></i>{}
            </a>        
        """.format(mapname, city.state.country.name)
        mapname += '@' + city.state.name
        html += """
            <a class="breadcrumb-item state-brcm" href="javascript:void();" data-mapname="{}">
                <i class="fa fa-long-arrow-right" aria-hidden="true"></i>{}
            </a>        
        """.format(mapname, city.state.name)
        mapname += '@' + str(city.id)
        html += """
            <a class="breadcrumb-item city-brcm" href="javascript:void();" data-mapname="{}">
                <i class="fa fa-long-arrow-right" aria-hidden="true"></i>{}
            </a>        
        """.format(mapname, city.name)

    elif kind == 2 or is_state == 'true': # - city
        country = mapName.split('/')[1].upper()
        state = State.objects.filter(name=state, country__sortname=country).first()
        cmapname = 'countries/{0}/{0}-all'.format(state.country.sortname.lower())
        html += """
            <a class="breadcrumb-item country-brcm" href="javascript:void();" data-mapname="{}">
                <i class="fa fa-long-arrow-right" aria-hidden="true"></i>{}
            </a>        
        """.format(cmapname, state.country.name)
        mapname = mapName if '@' in mapName else mapName + '@' + state.name
        html += """
            <a class="breadcrumb-item state-brcm" href="javascript:void();" data-mapname="{}">
                <i class="fa fa-long-arrow-right" aria-hidden="true"></i>{}
            </a>        
        """.format(mapname, state.name)
    elif kind == 1: # state
        country = mapName.split('/')[1].upper()
        country = Country.objects.filter(sortname=country).first()
        html += """
            <a class="breadcrumb-item country-brcm" href="javascript:void();" data-mapname="{}">
                <i class="fa fa-long-arrow-right" aria-hidden="true"></i>{}
            </a>        
        """.format(mapName, country.name)

    request.session['breadcrumb'] = html
    request.session.modified = True

    return HttpResponse(html)

def get_regions(request):
    """
    get regions like countries, states or cities
    and search link, list title
    """
    mapName = request.GET.get('mapName')
    state = request.GET.get('state').replace('%27', "'") \
                                    .replace('%20', " ")
    is_state = request.GET.get('is_state')
    city = request.GET.get('city')
    kind = mapName.count('-')

    if request.user.is_authenticated():
        # store last location
        loc = mapName
        if kind == 2 or is_state == 'true':
            loc += '@' + state 
        if city:
            loc += '@' + city
        request.user.default_site = loc
        request.user.save()

    request.session['category'] = ''

    if city:
        title = 'Select Category'
        link = '/region-ads/ct/{}'.format(city)
        request.session['region'] =  city
        request.session['region_kind'] = 'city'

        result = []
        for column in range(1, 7):
            _result = []
            for mc in Category.objects.filter(parent__isnull=True, column=column):
                cc = Category.objects.filter(parent=mc)
                _result += [(mc, cc)]
            result += [_result]
        html = render_to_string('_category.html', {'categories': result})            
    elif kind == 2 or is_state == 'true': # - city
        country = mapName.split('/')[1].upper()
        state = State.objects.filter(name=state, country__sortname=country).first()
        title = 'Select City'
        link = '/region-ads/st/{}'.format(state.id)
        request.session['region'] =  state.id
        request.session['region_kind'] = 'state'

        html = ''
        rs = City.objects.filter(state=state).order_by('name')
        for ii in rs:
            html += '<li><a href="javascript:void();" class="city_id" data-id="{1}">{0}</a></li>'.format(ii.name, ii.id)
        if html:
            html = '<ul class="country-list">' + html + '</ul>'
        else:
            html = '<ul class="country-list">No city found</ul>'
    elif kind == 0: # country
        title = 'Select Country'
        link = ''# '/region-ads/'
        request.session['region'] =  ''
        request.session['region_kind'] = 'world'

        html = ''
        rs = Country.objects.all()
        for ii in rs:
            html += '<li><a data-id="{}" class="country_id" href="javascript:void();">{}</a></li>'.format(ii.sortname.lower(), ii.name)
        html = '<ul class="country-list">' + html + '</ul>'
    elif kind == 1: # state
        country = mapName.split('/')[1].upper()
        country = Country.objects.filter(sortname=country).first()
        title = 'Select Region'
        link = ''#'/region-ads/{}'.format(country.id)
        request.session['region'] =  country.id
        request.session['region_kind'] = 'country'

        html = ''
        rs = State.objects.filter(country=country).order_by('name')
        for ii in rs:
            html += '<li data-id="{0}" class="region_id"><a href="javascript:void();">{0}</a></li>'.format(ii.name)
        html = '<ul class="country-list">' + html + '</ul>'

    request.session.modified = True

    result = {
        'title': title,
        'link': link,
        'html': html
    }

    return JsonResponse(result, safe=False)

@login_required(login_url='/accounts/login')
def post_ads(request, ads_id):
    if request.method == 'GET':
        mcategories = Category.objects.filter(parent__isnull=True)
        countries = Country.objects.all()
        
        if ads_id:
            post = Post.objects.get(id=ads_id)
            model = eval(post.category.form)
            post = model.objects.get(id=ads_id)
            states = State.objects.filter(country=post.region.state.country)
            cities = City.objects.filter(state=post.region.state)
            images = Image.objects.filter(post=post)
            detail_template = 'post/{}.html'.format(post.category.form)
        else:
            post = {}       # just for form
            states = None
            cities = None
            images = None
            detail_template = 'post/Post.html'

            if request.user.default_site:
                country = request.user.default_site.split('/')[1].upper()
                post['country'] = country       # country sortname
                states = State.objects.filter(country__sortname=country)
                loc = request.user.default_site.split('@')
                if len(loc) > 1:
                    state = loc[1]  # state name
                    post['state'] = state
                    cities = City.objects.filter(state__name=state)

                    if len(loc) > 2:
                        city = loc[2]   # city id
                        post['region_id'] = int(city)

        # print post, mcategories
        return render(request, 'post_ads.html', {
            'mcategories': mcategories,
            'countries': countries,
            'states': states,
            'cities': cities,
            'images': images,
            'post': post,
            'detail_template': detail_template,
            'skey': settings.STRIPE_KEYS['PUBLIC_KEY']
        })
    else:
        form_name = request.POST.get('ads_form') + 'Form'
        form = get_class(form_name)

        if ads_id:
            model = eval(request.POST.get('ads_form'))
            instance = model.objects.get(id=ads_id)
            form = form(request.POST, instance=instance)
        else:
            form = form(request.POST)

        # ignore last empty one due to template
        images = request.POST.getlist('uploded_id[]')[:-1]  
        
        if form.is_valid():
            post = form.save()
            pimages = [ii.name for ii in post.images.all()]

            # create objects for new images
            for img in list(set(images)-set(pimages)):
                Image.objects.create(post=post, name=img)

            # remove deleted ones
            for img in list(set(pimages)-set(images)):
                try:
                    os.remove(settings.BASE_DIR+'/static/media/'+img)
                except Exception:
                    pass
                Image.objects.filter(name=img).delete()


            price = int(post.category.price * 100)
            card = request.POST.get('stripeToken')
            if price and card:
                try:
                    stripe.Charge.create(
                        amount=price,
                        currency="usd",
                        source=card, # obtained with Stripe.js
                        description="Charge for Post(#{} - {})".format(post.id, post.title)
                    )
                except Exception, e:
                    print e, 'stripe error ##'
        print(form.errors, '$$$$$$$$')
        return HttpResponseRedirect(reverse('my-ads'))

def ulogout(request):
    logout(request)
    return HttpResponseRedirect(reverse('home'))

def get_sub_info(request):
    """
    ajax call for sub category, state, city
    """
    obj_id = request.GET.get('obj_id')
    sc_type = request.GET.get('type') # Category, State, City
    rndr_str = '<option value="">-Select-</option>'

    if sc_type == 'category':
        objects = Category.objects.filter(parent__id=obj_id)
    elif sc_type == 'state':
        objects = State.objects.filter(country__id=obj_id)
    else:
        objects = City.objects.filter(state__id=obj_id)
        
    for sc in objects:
        rndr_str += '<option value="{}">{}</option>'.format(sc.id, sc.name)
    return HttpResponse(rndr_str)

@csrf_exempt
def upload_image(request):
    myfile = request.FILES['images']
    _type = request.POST.get('type', '')
    if _type:
        _type = _type + '/' 

    fs = FileSystemStorage()
    filename = fs.save(_type+myfile.name, myfile)
    uploaded_file_url = fs.url(filename)
    res = {"image_url": uploaded_file_url,"image_name": uploaded_file_url.split('/')[-1]}
    return JsonResponse(res, safe=False)

@csrf_exempt
def delete_image(request):
    image_name = request.POST.get('image_name')
    # if not belong to any post
    if not Image.objects.filter(name=image_name):
        try:
            os.remove(settings.BASE_DIR+'/static/media/'+image_name)
        except Exception:
            pass
    return HttpResponse('')

def get_post_detail(request):
    obj_id = request.GET.get('obj_id')
    category = Category.objects.get(id=obj_id)
    form_name = category.form
    price = int(category.price * 100)
    template = 'post/{}.html'.format(form_name)
    html = render_to_string(template)

    return JsonResponse({'html': html, 'form': form_name, 'price': price}, safe=False)

@csrf_exempt
def active_deactive_ads(request):
    ads = request.POST.get('ads_id')
    status = request.POST.get('status')
    Post.objects.filter(id=ads).update(status=status)
    return HttpResponse('')

@csrf_exempt
def delete_ads(request):
    ads = request.POST.get('ads_id')
    Post.objects.filter(id=ads).delete()
    return HttpResponse('')

def view_ads(request, ads_id):
    post = get_object_or_404(Post, pk=ads_id)    
    images = post.images.all()
    favourite = False
    result = ''

    if request.user.is_authenticated():
        posts = [ii.post for ii in Favourite.objects.filter(owner=request.user)]
        favourite = post in posts

    if images:
        first_image = images[0].name
    else:
        first_image = 'dummy.jpg'

    if request.method == 'POST':
        optpay = request.POST.get('optpay')
        contact = request.POST.get('contact')
        card = request.POST.get('stripeToken')
        amount = int(post.price * 100)

        try:
            if optpay == "direct":
                stripe_account_id = '' #SocialAccount.objects.get(user__id=campaign.owner.id, provider='stripe').uid
                app_fee = 0.3

                charge = stripe.Charge.create(
                    amount=amount,
                    currency="usd",
                    source=card, # obtained with Stripe.js
                    # destination=stripe_account_id,
                    # application_fee = int(amount * app_fee),                
                    description="Direct pay to the ads (#{} - {})".format(post.id, post.title)
                )
            else:
                stripe_account_id = '' #SocialAccount.objects.get(user__id=campaign.owner.id, provider='stripe').uid
                app_fee = 0.3

                charge = stripe.Charge.create(
                    amount=amount,
                    currency="usd",
                    source=card, # obtained with Stripe.js
                    # destination=stripe_account_id,
                    # application_fee = int(amount * app_fee),                
                    description="Escrow for the ads (#{} - {})".format(post.id, post.title)
                )

            result = charge.id

            # send email to the owner
            content = "Ads (<a href='/ads/{}'>{}</a>) is purchased<br><br>Contact Info:<br>" \
                      .format(post.id, post.title)
            if perk:
                subject = 'Item purchased directly'
            else:
                subject = 'Item purchased via escrow'

            content += contact
            send_email(settings.FROM_EMAIL, subject, post.owner.email, content)

        except Exception as e:
            pass

    return render(request, 'ads_detail.html', {
        'post': post,
        'images': images,
        'first_image': first_image,
        'favourite': favourite,
        'skey': settings.STRIPE_KEYS['PUBLIC_KEY'],
        'result': result
    })

def view_campaign(request, camp_id):
    campaign = Campaign.objects.get(id=camp_id)
    perks = Perk.objects.filter(campaign=campaign)
    result = ''

    if request.method == 'POST':
        perk = request.POST.get('perk_id') or -1
        contact = request.POST.get('contact')
        amount = request.POST.get('amount')
        claimer = request.user if request.user.is_authenticated() else None
        card = request.POST.get('stripeToken')

        perk = Perk.objects.filter(id=perk).first()

        try:
            stripe_account_id = '' #SocialAccount.objects.get(user__id=campaign.owner.id, provider='stripe').uid
            app_fee = 0.3

            charge = stripe.Charge.create(
                amount=amount,
                currency="usd",
                source=card, # obtained with Stripe.js
                # destination=stripe_account_id,
                # application_fee = int(amount * app_fee),                
                description="Contribute to the Campaign (#{} - {})".format(campaign.id, campaign.title)
            )
    
            PerkClaim.objects.create(campaign_id=camp_id,
                                     perk=perk,
                                     contact=contact,
                                     claimer=claimer,
                                     amount=amount,
                                     transaction=charge.id)
            # send notification email to the owner
            if perk:
                subject = 'Perk Claimatoin from Globalboard'
                content = "Perk ({}) in the campaign ({}) is claimed<br><br>Contact Info:<br>" \
                          .format(perk.title, campaign.title)

                # update perk's claimed count, used for cache for less db transaction
                perk.num_claimed = perk.num_claimed + 1
                perk.save()
            else:
                subject = 'Donation to your campaign on Globalboard'
                content = "Donation (${}) is made to the campaign ({})<br><br>Contact Info:<br>" \
                          .format(int(amount)/100, campaign.title)

            content += contact
            send_email(settings.FROM_EMAIL, subject, campaign.owner.email, content)

            # update campaign's raised amount, used for cache for less db transaction
            campaign.raised = campaign.raised + int(amount) / 100
            campaign.save()

            result = charge.id
        except Exception, e:
            print e, 'stripe error ##'
            # result = 'failed'

        
    return render(request, 'camp_detail.html', {
        'post': campaign,
        'perks': perks,
        'skey': settings.STRIPE_KEYS['PUBLIC_KEY'],
        'result': result
    })

def category_ads(request, category_id):
    # store category
    request.session['category'] = category_id
    request.session.modified = True

    region_id = request.session.get('region')  # city
    if not region_id:
        return HttpResponseRedirect('/profile')

    region = City.objects.get(id=region_id)
    category = Category.objects.get(id=category_id)
    categories = Category.objects.filter(Q(id=category_id) | Q(parent__id=category_id))
    posts = Post.objects.filter(region=region, category__in=categories).exclude(status='deactive')
    posts = get_posts_with_image(posts)
    breadcrumb = request.session.get('breadcrumb', '<a class="breadcrumb-item" href="javascript:void();" data-mapname="custom/world">worldwide</a>')

    return render(request, 'ads-list.html', {
        'posts': posts,
        'region': region,
        'category': category,
        'others': True,
        'breadcrumb': breadcrumb
    })

@csrf_exempt
def send_friend_email(request):
    from_email = request.POST.get('from_email')
    to_email = request.POST.get('to_email')
    ads_id = request.POST.get('ads_id')
    post = Post.objects.get(id=ads_id)
    content = """
        {} forwarded you this from craigslist:<br><br>
        <h3>{}</h3><br><br>
        http://18.216.225.192/ads/{}
        """.format(from_email, post.title, post.id)

    send_email(settings.FROM_EMAIL, post.title, to_email, content)
    return HttpResponse('')

@csrf_exempt
def send_reply_email(request):
    from_email = request.POST.get('from_email')
    content = request.POST.get('content')
    ads_id = request.POST.get('ads_id')
    post = Post.objects.get(id=ads_id)

    subject = 'Reply to ' + post.title
    content = """
        {} <br><br>Original post: 
        http://18.216.225.192/ads/{}
        """.format(content, post.id)

    # print (from_email, subject, post.owner.email, content)
    send_email(from_email, subject, post.owner.email, content)
    return HttpResponse('')

def region_ads(request, region_id, region):
    if region == 'city':
        posts = Post.objects.filter(region_id=region_id)                            
    elif region == 'state':    
        posts = Post.objects.filter(region__state__id=region_id)
    elif region == 'world':
        posts = Post.objects.all()

    posts = get_posts_with_image(posts.exclude(status='deactive'))
    breadcrumb = request.session.get('breadcrumb', '<a class="breadcrumb-item" href="javascript:void();" data-mapname="custom/world">worldwide</a>')

    return render(request, 'ads-list.html', {
        'posts': posts,
        'region': region_id,
        'others': True,
        'breadcrumb': breadcrumb
    })

def globoard_display_world_countries(css_class=''):
    rndr_str = "<ul class='country-list {}'>".format(css_class)
    for country in Country.objects.all():
        rndr_str += '<li><a href="/profile#countries/{0}/{0}-all" class="show_country" data-country="{1}">{2}</a></li>'.format(country.sortname.lower(), country.sortname, country.name)
    return rndr_str + '</ul>'

@csrf_exempt
def toggle_favourite(request):
    ads_id = request.POST.get('ads_id')
    res = 'success'
    if request.user.is_authenticated():
        if Favourite.objects.filter(owner=request.user, post_id=ads_id):
            Favourite.objects.filter(owner=request.user, post_id=ads_id).delete()
        else:
            Favourite.objects.create(owner=request.user, post_id=ads_id)
    else:
        res = 'fail'

    return HttpResponse(res)

@login_required(login_url='/accounts/login')
def my_favourites(request):
    posts = [ii.post for ii in Favourite.objects.filter(owner=request.user)]
    posts = get_posts_with_image(posts)
    return render(request, 'ads-list.html', {'posts': posts, 'others': True})

@login_required(login_url='/accounts/login')
def my_subscribe(request):
    searches = Search.objects.filter(owner=request.user)

    return render(request, 'my-subscribe.html', {
        'searches': searches
    })

@csrf_exempt
def create_subscribe(request):
    keyword = request.POST.get('keyword')
    category = request.session['category']
    region_kind = request.session['region_kind']
    region_id = request.session['region']

    search = Search.objects.filter(owner=request.user, keyword=keyword)
    if category:
        search = search.filter(category_id=category)
    
    if region_kind == 'state':
        if not search.filter(state_id=region_id):
            Search.objects.create(**{
                'owner': request.user,
                'keyword': keyword,
                'category_id': category,
                'state_id': region_id
            })
    else:
        if not search.filter(city_id=region_id):
            Search.objects.create(**{
                'owner': request.user,
                'keyword': keyword,
                'category_id': category,
                'city_id': region_id
            })

    return HttpResponse('')

@csrf_exempt
def remove_subscribe(request):
    sub_id = request.POST.get('sub_id')

    Search.objects.filter(id=sub_id).delete()
    return HttpResponse('')

@login_required(login_url='/accounts/login')
def my_account(request):
    if request.method == 'GET':
        form = CustomerForm(instance=request.user)
    else:
        form = CustomerForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()

    return render(request, 'my-account.html', {'form': form})

@csrf_exempt
def send_vcode(request):
    phone = request.POST.get('phone')
    vcode = randint(100000, 999999)
    print vcode, '###'
    body = "{} is your Globalboard verification code.".format(vcode)
    result = send_SMS(phone, body)

    if result:
        request.session['vcode'] = str(vcode)
        request.session['phone'] = phone        
        request.session.modified = True    
        return HttpResponse('success')
    else:
        return HttpResponse('fail')

@csrf_exempt
def verify_phone(request):
    code = request.POST.get('vcode')
    vcode = request.session['vcode']

    if code == vcode:
        request.user.phone_verified = True
        request.user.phone = request.session['phone']        
        request.user.save()
        return HttpResponse('success')
    else:
        return HttpResponse('fail')

@csrf_exempt
def upload_id(request):
    id_photo = request.POST.get('id_photo')
    request.user.v_statue = 'awaiting_approve'
    # send an email to administrator
    content = """user {} uploaded his ID.<br> Please check and approve it 
                 <a href="http://18.216.225.192/admin/general/customer/{}/change/">here</a>.                 
    """.format(request.user.username, request.user.id)

    send_email(settings.FROM_EMAIL, 'Verification Submitted', settings.ADMIN_EMAIL, content)
    request.user.id_photo = 'ID/' + id_photo
    request.user.save()
    return HttpResponse('')

def confirm_phone(request):
    return render(request, 'account/phone_confirm.html')

@login_required(login_url='/accounts/login')
def my_campaigns(request):
    campaigns = Campaign.objects.filter(owner=request.user)

    return render(request, 'my-campaigns.html', {
        'campaigns': campaigns
    })

@login_required(login_url='/accounts/login')
def post_camp(request, camp_id):
    categories = CampCategory.objects.all()
    if request.method == 'GET':
        form = CampaignForm()
    else:
        form = CampaignForm(request.POST, request.FILES)

        if form.is_valid():
            camp = form.save()
            num_perks = int(request.POST.get('num_perks'))
            fs = FileSystemStorage()

            iii = 0
            for ii in range(num_perks):
                filename = None
                if request.POST.getlist('flag_perk_overview')[ii]:
                    perk_img = request.FILES.getlist('perk_overview')[iii]
                    filename = fs.save('perks/'+perk_img.name, perk_img)
                    iii += 1

                Perk.objects.create(title=request.POST.getlist('perk_title')[ii],
                                    campaign=camp,
                                    price=request.POST.getlist('perk_price')[ii],
                                    description=request.POST.getlist('perk_desc')[ii],
                                    num_avail=request.POST.getlist('perk_avail_num')[ii] or 1000000,
                                    image=filename)

            return HttpResponseRedirect(reverse('my-campaigns'))
    return render(request, 'post_camp.html', {
        'form': form,
        'categories': categories,   
        'rng_perks': range(1, 11)
    })

def explorer_campaigns(request):
    categories = CampCategory.objects.all()
    campaigns = Campaign.objects.all()[:10]

    return render(request, 'campaign-list.html', {
        'categories': categories,
        'campaigns': campaigns
    })

@csrf_exempt
def search_camps(request):
    keyword = request.POST.get('keyword')
    category = request.POST.get('category')
    others = request.POST.get('others')

    # if others:
        # .filter(owner=request.user)
    campaigns = Campaign.objects.filter(Q(title__icontains=keyword) | Q(overview__icontains=keyword) | Q(tagline__icontains=keyword))
    if category:
        campaigns = campaigns.filter(Q(category=category) | Q(category__parent=category))

    rndr_str = render_to_string('_camp_list.html', {'campaigns': campaigns[:20]})
    return HttpResponse(rndr_str)
