"Marketplace views."

from datetime import datetime, timedelta

from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response

from ripplesite.market.models import *
from ripplesite.ripple.views import checkLogin, getSessionInfos

"""
def checkDealsearchAction(request):
    try: # reload node from id every time to be safe, since it may have been changed by last request
        action = request.GET['btn']        
    except KeyError, NodeDoesNotExist:
        return None
    return action
"""

def searchads(request):
    "ad search form"

    if request.method == 'POST':
        action = request.POST['btn']
        category = request.POST['deal_category']
        location = request.POST['location']

        if (action == 'postoffered') :
            return HttpResponseRedirect('/market/new?type=offered&location=%s&category=%s' % (location,category) )
        if (action == 'postwanted') :
            return HttpResponseRedirect('/market/new?type=wanted&location=%s&category=%s' % (location,category) )
        if (action == 'searchoffered') :
            return HttpResponseRedirect('/market/showads?type=offered&location=%s&category=%s' % (location,category) )
        if (action == 'searchwanted') :
            return HttpResponseRedirect('/market/showads?type=wanted&location=%s&category=%s' % (location,category) )

    #if (action == 'postoffered' or action == 'postwanted') : return HttpResponseRedirect('/market/new/')
    #userNode = checkLogin(request) return HttpResponseRedirect('/' % request.path)
    #if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    d = {}
    #cutoff_date = datetime.now() - timedelta(days=30)
    #ads = Advertisement.objects.filter(posted_date__gt=cutoff_date)
    #ads = ads.order_by('-posted_date')
    #d['ads'] = ads
    #d['infos'] = getSessionInfos(request)
    return render_to_response('searchads.html', d, context_instance=RequestContext(request))

def showads(request):
    "Market front page.  View all ads in the last 30 days for now."

    # action = checkDealsearchAction(request)
    # to do: deal with these two cases separately

    #userNode = checkLogin(request) return HttpResponseRedirect('/' % request.path)
    #if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    d = {}
    cutoff_date = datetime.now() - timedelta(days=30)

    showWanted = request.GET.get('type') == "wanted" 

    ads = Advertisement.objects.filter(posted_date__gt=cutoff_date,wanted=showWanted)
    ads = ads.order_by('-posted_date')
    d['ads'] = ads
    d['infos'] = getSessionInfos(request)
    d['values'] = request.GET
    return render_to_response('ad_list.html', d, context_instance=RequestContext(request))

def main(request):
    "Market front page.  View all ads in the last 30 days for now."

    #action = checkDealsearchAction(request)
    # to do: deal with these two cases separately

    #userNode = checkLogin(request) return HttpResponseRedirect('/' % request.path)
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
    if not userNode: return HttpResponseRedirect('/login/?redirect=/' )
    d = {}

    if request.method == 'POST':
        
        errors = []
        if not request.POST.get('title'):
            errors.append('Your post must have a subject.')
        if not request.POST.get('text'):
            errors.append('Your post must have a body.')
        if not request.POST.get('location'):
            errors.append('Your post must have a location.')
        if not request.POST.get('category'):
            errors.append('Your post must have a category.')
        if not request.POST.get('text'):
            errors.append('Your post must have a body.')
        if not request.POST.get('wanted'):
            errors.append('Your post must have specify wanted or offered.')


        
        if not errors:
            

            ad = Advertisement(user=userNode,
                               location=request.POST['location'],
                               category=request.POST['category'],
                               title=request.POST['title'],
                               text=request.POST['text'],
                               wanted= (request.POST['wanted']=="wanted") )
                               #wanted=False)
                               

            #try:
            ad.save()
            request.session['infos'] = ['Your new post has been added.']
            return HttpResponseRedirect('/market/showads?type=' + request.POST['wanted'])
        else:
            d['values'] = request.POST
            d['infos'] = errors
            

    else:
        d['values'] = request.GET
        d['request'] = getSessionInfos(request)
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

