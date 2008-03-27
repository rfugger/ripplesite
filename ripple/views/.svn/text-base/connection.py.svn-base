# RippleSite Standalone Ripple Web Service Software
# Copyright (C) 2006-07
# 
# This program is free software; you can redistribute it and/or modify it 
# under the terms of the GNU General Public License as published by the 
# Free Software Foundation; either version 2 of the License, or (at your 
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General 
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along 
# with this program; if not, write to the Free Software Foundation, Inc., 
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# Ryan Fugger
# ryan@ripplepay.com
#-------------------------------------------------------------------------

"""
Django views for connection accounts
"""

from django.core import template_loader
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.conf import settings
from django.db.models import Q
from django.utils.html import escape

from ripplesite.ripple.models import *
from ripplesite.ripple.views import checkLogin, getAccountsSummary, parseEmails, getEmails, Struct, sendEmail, getSessionInfos, getRateProposalAccts
import routing
from pathgraph import computeInterest

import datetime


def accountList(request):
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    
    d = {}
    d['infos'] = getSessionInfos(request)
    
    d['accountCurrencies'] = getAccountsSummary(userNode)
    
      # outstanding offers of credit received/made
    d['receivedOffers'] = Offer.objects.filter(recipient_email__in=getEmails(userNode)).order_by('-id')
    d['sentOffers'] = userNode.sent_offer_set.order_by('-id')
    d['rateProposals'] = getRateProposalAccts(userNode)
    return render_to_response('accountList.html', d, context_instance=RequestContext(request))

def accountDetail(request, acctId):
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)

    if Account.objects.filter(pk=acctId).count() > 0:
        acct = Account.objects.get(pk=acctId)
    else: # can't access accounts that aren't in database and active
        return HttpResponseRedirect('/accounts/')
    
    if acct.owner_id != userNode.id: # can't access accounts that aren't yours!
        return HttpResponseRedirect('/accounts/')
    
    d = {}
    d['infos'] = getSessionInfos(request)
    
    if request.method == 'POST': # modify account or set error
        if request.POST['name'] == '':
            d['infos'].append("Error: Account name can't be left blank.")
        elif acct.name != request.POST['name']:
            acct.name = request.POST['name']
            d['infos'].append("Account name changed.")
        
        try:
            interest_rate = float(request.POST['interest']) / 100.0 # may raise ValueError
            shared_data = acct.shared_data
            if interest_rate <> shared_data.interest_rate:
                if shared_data.proposed_rate and interest_rate == shared_data.proposed_rate and userNode.id == shared_data.node_to_confirm_id:
                    # take manually setting to otherly-proposed rate to be acceptance
                    accept_proposed_rate(request, shared_data)
                    d['infos'].append("Interest rate set to %s%%." % (interest_rate * 100.0))
                else:
                    info = propose_rate(request, shared_data, interest_rate, node_to_confirm=acct.partner)
                    d['infos'].append(info)
                    
        except ValueError:
            d['infos'].append("Interest rate must be a number.")
        
        try: # modify partner's max credit limit
            partner_limit = float(request.POST['partner_limit'])
            if partner_limit < 0.0:
                d['infos'].append("Error: Partner's credit limit must be a positive number or zero. '%s' is invalid." % request.POST['partner_limit'])
                raise ValueError
            elif partner_limit >= 1e12:
                d['infos'].append("Error: Partner limit amount is too large to be stored in the database.  Please enter another amount.")
                raise ValueError
            elif partner_limit <= 1e-12 and partner_limit != 0.0:
                d['infos'].append("Error: Partner limit amount is too small to be stored in the database.  Please enter another amount.")
                raise ValueError
            
            if acct.partner_limit != partner_limit:
                acct.partner_limit = partner_limit
                d['infos'].append("Partner has been offered a credit limit of up to %.2f." % acct.partner_limit)
                # modify partner's actual iou limit if necessary
                partnerAcct = acct.get_partner_acct()
                oldPartnerIOULimit = partnerAcct.iou_limit
                if partnerAcct.my_limit != None:
                    partnerAcct.iou_limit = min(partnerAcct.my_limit, acct.partner_limit)
                else:
                    partnerAcct.iou_limit = acct.partner_limit
                if partnerAcct.iou_limit != oldPartnerIOULimit:
                    partnerAcct.save()
                    if acct.partner_limit == partnerAcct.iou_limit:
                        d['infos'].pop() # clear mesage about partner being offered credit
                    d['infos'].append("Partner's credit limit changed to %.2f." % partnerAcct.iou_limit)

        except ValueError:
            d['infos'].append("Partner's credit limit must be a number.")
        
        if request.POST['my_limit'] != '':
            try: # modify my max credit limit
                my_limit = float(request.POST['my_limit'])
                if my_limit < 0.0:
                    d['infos'].append("Error: My credit limit must be a positive number or zero. '%s' is invalid." % request.POST['my_limit'])
                    raise ValueError
                elif my_limit >= 1e12:
                    d['infos'].append("Error: My credit limit amount is too large to be stored in the database.  Please enter another amount.")
                    raise ValueError
                elif my_limit <= 1e-12:
                    d['infos'].append("Error: My credit limit amount is too small to be stored in the database.  Please enter another amount.")
                    raise ValueError
                
                if acct.my_limit != my_limit:
                    acct.my_limit = my_limit
                    d['infos'].append("You have chosen to automatically accept a credit limit of up to %.2f from your partner." % acct.my_limit)
            
            except ValueError:
                d['infos'].append("My credit limit must be a number.")
        
        else: # set my limit to None = unlimited
            if acct.my_limit != None: # only change if not already None
                acct.my_limit = None
                d['infos'].append("You have chosen to automatically accept as high a credit limit as your partner offers you.")
        
        # modify my actual iou limit if necessary
        oldIOULimit = acct.iou_limit
        if acct.my_limit != None:
            acct.iou_limit = min(acct.my_limit, acct.get_partner_acct().partner_limit)
        else: # my_limit = unlimited
            acct.iou_limit = acct.get_partner_acct().partner_limit
        if acct.iou_limit != oldIOULimit:
            if acct.iou_limit == acct.my_limit:
                d['infos'].pop() # clear message about my maximum credit limit
            d['infos'].append("My credit limit changed to %.2f" % acct.iou_limit)

        acct.save()

        request.session['infos'] = d['infos']
        return HttpResponseRedirect('.')

    # render account details page
    # *** probably just need to pass acct, and maybe units
    d['cur'] = acct.shared_data.currency
    d['acct'] = acct
    d['balance'] = acct.getBalance()
    #d['avgBalance'] = averageBalance(acct, 30)
    d['lowerLimit'] = acct.iou_limit
    d['upperLimit'] = acct.get_partner_acct().iou_limit
    d['displayBalance'] = d['balance']
    #d['displayAvgBalance'] = d['avgBalance']
    d['displayLowerLimit'] = d['lowerLimit']
    d['displayUpperLimit'] = d['upperLimit']
    if userNode.display_units_id and d['cur'].value:
        rate = d['cur'].value / userNode.display_units.value
        d['displayBalance'] *= rate
        #d['displayAvgBalance'] *= rate
        d['displayLowerLimit'] *= rate
        d['displayUpperLimit'] *= rate
    if d['cur'].value:
        d['convertibleUnits'] = CurrencyUnit.objects.filter(value__gt=0.0).order_by('long_name')
    d['closeable'] = (float('%.2f' % d['balance']) == 0.0)
    
    # get links for payments touching this account
    paymentTotal = 0.0
    months = []
    now = datetime.datetime.now()
    year = now.year
    month_num = now.month
    balance = acct.getBalance()
    highlight_row = False
    while True: # go month-by-month back to account creation
        month = {}
        links, interest, date = getLinksandInterestForMonth(acct, year, month_num)
        if year == now.year and month_num == now.month:
            interest += acct.getPresentInterest()
        else:
            month['date'] = date
        month['interest'] = interest
        month['balance'] = balance - paymentTotal
        if interest:
            month['highlight_row'] = highlight_row
            highlight_row = not highlight_row
        paymentTotal += interest
        months.append(month)

        entries = []
        last_entry = None
        for link in links:
            link.balance = balance - paymentTotal
            paymentTotal += link.amount
            if last_entry and last_entry.path.payment_id == link.path.payment_id:
                last_entry.amount += link.amount
            else:
                link.highlight_row = highlight_row
                highlight_row = not highlight_row
                entries.append(link)
                last_entry = link
        month['links'] = entries
        
        if month_num == 1:
            month_num = 12
            year = year -1
        else:
            month_num -= 1
        
        if datetime.datetime(year, month_num, 1) < acct.shared_data.created:
            break
    
    d['months'] = months
    d['paymentTotal'] = paymentTotal
    
    return render_to_response('accountDetail.html', d, context_instance=RequestContext(request))

def getLinksandInterestForMonth(acct, year, month):
    month_start = datetime.date(year=year, month=month, day=1)
    if month == 12:
        next_month_start = datetime.date(year=year + 1, month=1, day=1)
    else:
        next_month_start = datetime.date(year=year, month=month + 1, day=1)
    links = PaymentLink.objects.filter(payer_account__id__in=(acct.id, acct.get_partner_acct().id)
                                          ).extra(select={'date': 'pmt.date'},
                                                          tables=['ripple_paymentpath as path',
                                                                          'ripple_payment as pmt'],
                                                          where=['ripple_paymentlink.path_id=path.id',
                                                                        'path.payment_id=pmt.id',
                                                                        "pmt.date >= '%s'",
                                                                        "pmt.date < '%s'"],
                                                          params=[month_start, next_month_start]).order_by('-date')
    sum = 0.0
    for link in links:
        if link.payer_account_id == acct.id:
            link.interest = -link.interest # these amounts appear as negative (outgoing payments)
            link.amount = -link.amount
        sum += link.interest
        
    last_date = None
    if links:
        last_date = links[0].date
    return links, sum, last_date


# calculate time-weighted average of through payments
# added to sum of end-point payments
# period - in days
# **** FLAWED - can give different average to each partner ****
def averageBalance(acct, period):
    now = datetime.datetime.now()
    start = now - datetime.timedelta(days=period)
    links = PaymentLink.objects.filter(path__payment__date__gt=start, payer_account__id__in=(acct.id, acct.partner_acct_id)
                                                        ).order_by('-ripple_payment.date') 
    syntheticBal = 0.0 # balance of thru-payments, moving backwards starting at zero
    averageBal = acct.getBalance() # what we're computing
    prevPmtTime = now
    prevPmtAmount = 0.0
    for link in links:
        # make sure link is for thru-payment
        if link.payer_account_id != acct.id or link.position != 1: # not payer
            if link.payer_account_id == acct.id or link.position != PaymentLink.objects.filter(path__pk=link.path_id).count(): # not recipient
                syntheticBal -= prevPmtAmount
                linkTime = link.path.payment.date
                delta = prevPmtTime - linkTime
                # adjust by synthetic balance times fraction of period at that balance
                delta_days = delta.days + (delta.seconds + float(delta.microseconds) / 1000000) / 86400
                averageBal += syntheticBal * delta_days / period
                if link.payer_account_id == acct.id: # link is outgoing pmt on this acct
                    prevPmtAmount = -link.amount
                else: # link is incoming pmt on this acct
                    prevPmtAmount = link.amount
                prevPmtTime = linkTime
    
    # now factor in time from start of period to first paymentlink (last in list)
    syntheticBal -= prevPmtAmount
    delta = prevPmtTime - start
    delta_days = delta.days + (delta.seconds + float(delta.microseconds) / 1000000) / 86400
    averageBal += syntheticBal * delta_days / period
    
    return averageBal

def confirmClose(request, acctId):
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    
    if not Account.objects.filter(pk=acctId).count() > 0:
        return HttpResponseRedirect('/accounts/')
    
    d = {}
    d['acct'] = Account.objects.get(pk=acctId)
    if d['acct'].owner_id != userNode.id:
        return HttpResponseRedirect('/accounts/')
    return render_to_response('confirmClose.html', d, context_instance=RequestContext(request))

# for closing account and anything else we might want to do to the account
def accountAction(request, acctId, action):
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/accounts/%s/' % acctId)
    
    if request.method == 'POST':
        if request.POST['submit'] == 'Cancel':
            return HttpResponseRedirect('/accounts/%s/' % acctId)
    
    if Account.objects.filter(pk=acctId).count() == 0:
        return HttpResponseRedirect('/accounts/')
    
    acct = Account.objects.get(pk=acctId)
    if acct.owner_id != userNode.id:
        return HttpResponseRedirect('/accounts/')
    
    if action == 'close':
        sharedData = acct.shared_data
        if abs(sharedData.balance) >= 0.005:
            request.session['infos'] = ["Account balance must be zero before it can be closed."]
            return HttpResponseRedirect('/accounts/%d/' % acct.id)
        
        # to be sure a transaction doesn't hit this account before it gets
        # deactivated, set limits to zero, save, and then check for zero balance again
        myIOULimit = acct.iou_limit
        partnerAcct = acct.get_partner_acct()
        partnerIOULimit = partnerAcct.iou_limit
        acct.iou_limit = 0.0
        acct.save()
        partnerAcct.iou_limit = 0.0
        partnerAcct.save()
        
        if abs(sharedData.balance) >= 0.005:
            request.session['infos'] = ["Account balance must be zero before it can be closed."]
            # restore limits on accts
            acct.iou_limit = myIOULimit
            acct.save()
            partnerAcct.iou_limit = partnerIOULimit
            partnerAcct.save()
            return HttpResponseRedirect('/accounts/%d/' % acct.id)
        
        # now it's impossible for a transaction to change the balance, and the balance is zero, so:
        sharedData.active = False
        sharedData.save()
        
        # notify user
        request.session['infos'] = ["Account %d (%s) closed." % (sharedData.id, acct.name)]
        
        # notify partner by email
        note = ''
        if request.method == 'POST':
            note = request.POST['note']
        t = template_loader.get_template('emailAcctClosed.txt')
        c = RequestContext(request, {'acct':partnerAcct, 'note':note})
        sendEmail("One of your accounts has been closed", t.render(c), acct.partner.getPrimaryEmail())
        pass
        
        return HttpResponseRedirect('/accounts/')

# process form from offerToEmails
def offer(request):
    """offer credit to multiple nodes"""
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    
    if not request.POST:
        return HttpResponseRedirect('/summary/')

    if request.POST['phase'] == 'make_offers': # check if offers are finalized, or if we're just listing emails and the form
        # extract info from POST dictionary
        rows = []
        for i in range(0, int(request.POST['count'])):
            row = Struct()
            row.email = request.POST['email_%d' % i] # already parsed as email addresses
            row.amount = request.POST['amount_%d' % i]
            row.currency = request.POST['currency_%d' % i]
            row.interest = request.POST['interest_%d' % i]
            rows.append(row)

        # find errors in entries
        error = False
        for row in rows:
            # ensure no double-offers or double-accounts
            emailList, errors = validateOfferEmails([row.email], userNode)
            if not emailList: # if row.email is in list, then offer is valid
                error = True
                row.error = errors[0] # only show first error
                continue # only one error per row

            # validate amounts as numbers
            try:
                row.amount = float(row.amount)
                if row.amount <= 0.0:
                    raise ValueError
            except ValueError:
                error = True
                row.error = "Credit limit must be a number greater than zero."
            else:
                if row.amount >= 10**12:
                    error = True
                    row.error = "Amount is too large to be stored in the database.  Please enter another amount."
                elif row.amount <= 10**-12:
                    error = True
                    row.error = "Amount is too small to be stored in the database.  Please enter another amount."
            
            if error:
                continue # only one error per row
            
            try:
                row.interest = float(row.interest)
            except ValueError:
                error = True
                row.error = "Interest rate must be a number."
        
        note = request.POST['note']
        if note == '': note = None
        
        if error: # show form again with errors and values still there (in row objects)
            d = {'rows':rows, 'count':len(rows)}
            d['infos'] = ["One of more of your entries had errors. Please make corrections below."]
        else: # create and save offers, and send out emails
            infos = []
            infos.append('The system has recorded your offers of credit and is sending out invitation emails.  <a href="/accounts/#offers">Click here to see your offers.</a>')
            #infos.append("If the invitation does not arrive, it may be in the destination's spam folder...")
            for row in rows:
                currency = CurrencyUnit.objects.get(short_name=row.currency)
                offer = Offer(initiator=userNode, recipient_email=row.email, 
                                                          amount=row.amount, currency=currency, interest_rate=row.interest)
                offer.save()

                # send out email
                t = template_loader.get_template('emailInvitation.txt')
                c = RequestContext(request, {'row':row, 'userNode':userNode, 'currency':currency, 'note':note})
                sender = '"%s" <%s>' % (userNode.name, userNode.getPrimaryEmail())
                if not sendEmail('Invitation to Ripple', t.render(c), row.email, sender=sender, attempts=2, includeServiceName=False):
                    infos.append("An email could not be sent to %s, but your offer has been stored. Please contact %s manually." % (escape(row.email), escape(row.email)))
            request.session['infos'] = infos
            return HttpResponseRedirect('/accounts/')

    else: # else, list emails + form
        emails = parseEmails(request.POST['emailText'])
        emails, infos = validateOfferEmails(emails, userNode)
        if emails == [] and infos == []:
            infos.append("You didn't enter any valid email addresses.")
        rows = []
        for email in emails:
            row = Struct()
            row.email = email
            row.currency = None
            row.interest = 0
            rows.append(row)
        d = {'infos':infos, 'rows':rows, 'count':len(rows)}
    
    d['currencies'] = CurrencyUnit.objects.order_by('long_name')
    return render_to_response('offer.html', d, context_instance=RequestContext(request))

def validateOfferEmails(emails, userNode):
    infos = []
    for email in emails[:]: # use slice operator to make a copy of emails because it will be modified during loop
        remove = False
        
        # check if email address belongs to someone
        if EmailAddr.objects.filter(email=email).count() > 0:
            emailAddr = EmailAddr.objects.get(email=email)
            
            # check if user already has account with owner of this email address
            if Account.objects.filter(owner=userNode, partner__pk=emailAddr.node_id, shared_data__active=True).count() != 0:
                remove = True
                acct = Account.objects.get(owner=userNode, partner__pk=emailAddr.node_id, shared_data__active=True)
                infos.append('You already have an account with %s. <a href="/accounts/%d/">You can modify it here.</a>' % (escape(email), acct.id))
            
            # check if email address has made an offer to this user
            if Offer.objects.filter(recipient_email__in=getEmails(userNode), initiator__pk=emailAddr.node_id).count() != 0:
                remove = True
                offer = Offer.objects.filter(recipient_email__in=getEmails(userNode), initiator__pk=emailAddr.node_id)[0]
                infos.append('%s has already offered <b>you</b> %s %.2f credit. <a href="/offers/%d/accept/">Click here to accept.</a>' % (escape(email), offer.currency.short_name, escape(offer.amount), offer.id))
                
        # check if user has already made an offer to this email address
        if Offer.objects.filter(initiator=userNode, recipient_email=email).count() != 0:
            remove = True
            offer = Offer.objects.get(initiator=userNode, recipient_email=email)
            infos.append('You have already made an offer to %s. <a href="/offers/%d/withdraw/">Click here to withdraw it.</a>' % (escape(email), offer.id))
        
        # remove userNode's email if present
        if email in getEmails(userNode, confirmed=False):
            remove = True
            infos.append("You can't connect to yourself! Silly monkey.")
        
        if remove:
            emails.remove(email)

    return emails, infos

def rejectionNote(request, offerId):
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    
    if Offer.objects.filter(pk=offerId).count() == 0:
        request.session['infos'] = ["Offer has been withdrawn by the sender."]
        return HttpResponseRedirect('/summary/')
    
    offer = Offer.objects.get(pk=offerId)
    if offer.recipient_email not in getEmails(userNode):
        return HttpResponseRedirect('/summary/')
    
    d = {'offer': offer}
    return render_to_response('rejectionNote.html', d, context_instance=RequestContext(request))
    

def offerAction(request, offerId, action):
    """Accept or reject somebodys offer of credit"""
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    
    message = ''
    if Offer.objects.filter(pk=offerId).count() == 1:
        offer = Offer.objects.get(pk=offerId)
    else: # offer has been deleted since action link was displayed to user
        if action == 'accept' or action == 'reject':
            message = "Offer has been withdrawn and cannot be accepted or rejected."
        else:
            message = "Offer has already been acted on and cannot be withdrawn."
        request.session['infos'] = [message]
        return HttpResponseRedirect('/summary/')

    # check the offer is for the logged-in user if action is accept or reject
    if (action == 'accept' or action == 'reject') and \
            offer.recipient_email not in getEmails(userNode):
        return HttpResponseRedirect('/summary/')

    if action == 'accept':
        initiator = offer.initiator
        # check for existing account between nodes
        # *** temporary until multiple accounts permitted
        if Account.objects.filter(owner=userNode, partner=initiator, shared_data__active=True).count() > 0:
            request.session['infos'] = ["Account already exists with %s.  Multiple accounts with the same neighbour are not permitted (yet)." % escape(initiator.name)]
            offer.delete()
            return HttpResponseRedirect('/summary/')
        currencyId = offer.currency_id
        shared = SharedAccountData(currency_id=currencyId, balance=0.0, active=True,
                                                              interest_rate=offer.interest_rate/100.0)
        shared.save()
        acct1 = Account(owner=initiator, partner=userNode, shared_data=shared, balance_multiplier=1, 
                                        iou_limit=0.0, partner_limit=offer.amount, name=userNode.name)
        acct1.save()
        acct2 = Account(owner=userNode, partner=initiator, shared_data=shared, balance_multiplier=-1, 
                                        iou_limit=offer.amount, partner_limit=0.0, name=initiator.name)
        acct2.save()
        offer.delete()
        
        # shuffle node locations *** slow - consider doing as a regular script instead
        circle = routing.Circle()
        circle.shuffle(10 * Node.objects.count())
        
        # send email informing initiator that offer was accepted
        t = template_loader.get_template('emailInvitationAccepted.txt')
        c = RequestContext(request, {'offer':offer, 'acct':acct1})
        sendEmail("Invitation accepted", t.render(c), initiator.getPrimaryEmail())
        
        request.session['infos'] = ["This is your new connection account with %s.  Please take the time to give your account a meaningful name and assign your new neighbour a credit limit." % escape(initiator.getPrimaryEmail())]
        return HttpResponseRedirect('/accounts/%d/' % acct2.id)
    elif action == 'reject':
        offer.delete()
        
        note = ''
        if request.method == 'POST':
            note = request.POST['note']
        
        # send email informing initiator that offer was rejected
        t = template_loader.get_template('emailInvitationRejected.txt')
        c = RequestContext(request, {'offer':offer, 'note':note})
        sendEmail("Your invitation was not accepted", t.render(c), offer.initiator.getPrimaryEmail())
        
        message = "Offer from %s rejected." % escape(offer.initiator.getPrimaryEmail())
    elif action == 'withdraw':
        if userNode != offer.initiator:
            return HttpResponseRedirect('/accounts/')
        offer.delete()
        message = "Offer to %s withdrawn." % offer.recipient_email

    if message:
        request.session['infos'] = [message]
    return HttpResponseRedirect('/accounts/')


def interestRateAction(request, acctId, action):
    "Accept or reject a rate-change proposal on an account."
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    
    if Account.objects.filter(owner=userNode, pk=acctId).count() == 0:
        return HttpResponseRedirect('/accounts/')
    
    acct = Account.objects.get(pk=acctId)
    shared_data = acct.shared_data
    if shared_data.proposed_rate <> None and shared_data.node_to_confirm_id == userNode.id:
        if action == 'accept':
            accept_proposed_rate(request, shared_data)
        elif action == 'reject':
            reject_proposed_rate(request, shared_data)
    
    return HttpResponseRedirect('/accounts/%d/' % acct.id)

def accept_proposed_rate(request, shared_data):
        # this is node_to_confirm's account
        acct = Account.objects.get(shared_data=shared_data, owner__pk=shared_data.node_to_confirm_id)
        
        pmt = None
        
        if acct.getBalance() and shared_data.interest_rate: # otherwise no update necessary

                pmt = Payment(payer=acct.owner,
                                            payer_email=acct.owner.getPrimaryEmail(),
                                            recipient=acct.partner,
                                            recipient_email=acct.partner.getPrimaryEmail(),
                                            currency=shared_data.currency,
                                            amount=0.0,
                                            status='PE',
                                            description='Interest rate change: %s%% to %s%%.' % \
                                            (shared_data.displayRate(), shared_data.displayProposedRate()))
                pmt.save() # set pmt time
                #pmt = Payment.objects.get(pk=pmt.id) # reload because django doesn't update date that is auto-set on save
                
                interest = computeInterest(acct.getBalance(), shared_data.interest_rate, shared_data.last_update, pmt.date)
                
                path = PaymentPath(payment=pmt, amount=pmt.amount)
                path.save()
                
                link = PaymentLink(path=path, payer_account=acct, position=1, 
                                                                                amount=pmt.amount, interest=-interest, 
                                                                                interest_rate=shared_data.interest_rate)
                link.save()
                
                shared_data.balance += interest * acct.balance_multiplier
                
        if pmt:
                shared_data.last_update = pmt.date
        else:
                shared_data.last_update = datetime.datetime.now()
        shared_data.interest_rate = shared_data.proposed_rate
        shared_data.proposed_rate = None
        shared_data.node_to_confirm_id = None
        shared_data.save()

        if pmt: # could do this initially now that this is wrapped in a transaction
                pmt.status = 'OK'
                pmt.save()
  
        t = template_loader.get_template('emailAcceptRateProposal.txt')
        c = RequestContext(request, {'acct': acct.get_partner_acct()})
        sendEmail("Interest rate proposal accepted", t.render(c), acct.partner.getPrimaryEmail())

def reject_proposed_rate(request, shared_data):
    
    proposed_rate = shared_data.proposed_rate * 100.0
    partner_acct = Account.objects.exclude(owner__pk=shared_data.node_to_confirm_id).get(shared_data=shared_data)
    shared_data.proposed_rate = None
    shared_data.node_to_confirm_id = None
    shared_data.save()
    
    t = template_loader.get_template('emailRejectRateProposal.txt')
    c = RequestContext(request, {'acct': partner_acct, 'proposed_rate': proposed_rate})
    sendEmail("Interest rate proposal not accepted", t.render(c), partner_acct.owner.getPrimaryEmail())

def propose_rate(request, shared_data, interest_rate, node_to_confirm):
    acct_to_confirm = Account.objects.get(shared_data=shared_data, owner=node_to_confirm)
    shared_data.proposed_rate = interest_rate
    shared_data.node_to_confirm_id = node_to_confirm.id
    shared_data.save()
    
    t = template_loader.get_template('emailInterestRateProposal.txt')
    c = RequestContext(request, {'acct': acct_to_confirm})
    if sendEmail("Interest rate proposal", t.render(c), node_to_confirm.getPrimaryEmail(), attempts=2):
        return "Your partner has been notified of your proposed rate change."
    else:
        return "Your rate proposal has been recorded, however, the system could not send an email notifying them.  Please contact them manually."
