"Marketplace views."

from datetime import datetime, timedelta

from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response

from ripplesite.market.models import *
from ripplesite.ripple.views import checkLogin, getSessionInfos

def main(request):
    "Market front page.  View all ads in the last 30 days for now."
    userNode = checkLogin(request)
    #if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    d = {}
    cutoff_date = datetime.now() - timedelta(days=30)
    ads = Advertisement.objects.filter(posted_date__gt=cutoff_date)
    ads = ads.order_by('-posted_date')
    d['ads'] = ads
    d['infos'] = getSessionInfos(request)
    return render_to_response('ad_list.html', d, context_instance=RequestContext(request))

def new_ad(request):
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    d = {}
    if request.method == 'POST':
        errors = []
        if not request.POST.get('title'):
            errors.append('Your post must have a subject.')
        if not request.POST.get('text'):
            errors.append('Your post must have a body.')
        if not errors:
            ad = Advertisement(user=userNode,
                               title=request.POST['title'],
                               text=request.POST['text'])
            ad.save()
            request.session['infos'] = ['Your new post has been added.']
            return HttpResponseRedirect('../')
        else:
            d['values'] = request.POST
            d['infos'] = errors
    d['infos'] = getSessionInfos(request)
    return render_to_response('new_ad.html', d, context_instance=RequestContext(request))

def view_ad(request, ad_id):

    d = {}
    d['userNode'] = checkLogin(request)
    #if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    try:
        ad = Advertisement.objects.get(pk=ad_id)
    except Advertisement.DoesNotExist:
        return HttpResponseRedirect('../')

    
    if request.method == 'POST':
        # *** todo: actually send an email here.
        request.session['infos'] = ['Your message has been sent to the seller.']
        return HttpResponseRedirect('.')
    
    d['ad'] = ad
    d['infos'] = getSessionInfos(request)
    d['request'] = request
    return render_to_response('view_ad.html', d, context_instance=RequestContext(request))

