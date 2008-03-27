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
Ripple payment module

To Do:
#todo: check last-updated date on each account in link-insert sql to be sure interest doesn't get added twice
#todo: use Decimals for correct precision?
#todo: use Django's db connection for transactions?
"""

from datetime import datetime

from django.core import template_loader
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.db.models import Q
from django.conf import settings
from django.utils.html import escape
from django.db import transaction

from ripplesite.ripple.models import *
from ripplesite.ripple.views import checkLogin, sendEmail, getSessionInfos
import routing
import psycopg as db_module # *** change 'psycopg' to 'MySQLdb' for MySQL

from pathgraph import PathGraph, computeInterest
from dbconnect import DSN

VERBOSE = settings.DEBUG

# PaymentError codes
NO_PATH, TX_COLLISION, OVERPAYMENT, DB_ERROR, LINK_INSERT_FAILED, BAL_UPDATE_FAILED = range(6)

#------------- Django views ----------------------------

def paymentForm(request, pmtId=None, otherUserId=None, is_request=False):
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    errors = []
    d = {}
    
    if request.method == 'POST': # get post data and attempt payment
        email = request.POST['email']
        d['email'] = email # for maintaining form value in case of error
        if EmailAddr.objects.filter(email=email, confirmed=True).count() == 0:
            errors.append("Email '%s' does not belong to any Ripple user,"
                          "or has not yet been confirmed." % escape(email))
        else:
            emailAddr = EmailAddr.objects.get(email=email)
            otherUser = emailAddr.node
            if otherUser == userNode:
                action = is_request and 'request payment from' or 'pay'
                errors.append("You can't %s yourself." % action)
        
        amountStr = request.POST['amount']
        d['amount'] = amountStr
        try:
            amount = float(amountStr)
            if amount <= 0.0:
                raise Exception
        except:
            errors.append("Amount must be a positive number. '%s' is not valid." % escape(amountStr))
        
        currencyName = request.POST['currency'] # this should be OK, since it's from a generated list
        currency = CurrencyUnit.objects.get(short_name=currencyName)
        d['selectedUnitId'] = currency.id
        
        d['description'] = request.POST['description']
        
        if not errors: 
            # check for enough credit
            available = availableCredit(userNode, currency, incoming=is_request)
            if available < amount:
                action = is_request and 'request' or 'make'
                errors.append("You do not have enough available credit to %s payment.  "
                              "Available: %s %.2f." % (action, currency.short_name, available))
            if availableCredit(otherUser, currency, incoming=not is_request) < amount:
                if is_request:
                    pass  # Other user might get more credit to fulfill request
                else:
                    errors.append("Your intended recipient has not offered enough credit "
                                  "to receive your payment.")

        pmt = None
        if request.POST['pmtId'] != 'None':
            pmt = Payment.objects.get(pk=request.POST['pmtId'])
            # Check if user can edit
            if (not is_request and pmt.payer_id != userNode.id) or \
                    (is_request and pmt.recipient_id != userNode.id):
                return HttpResponseRedirect('/payments/')
            if pmt.status == 'OK': # can't edit completed payment
                d = {'message':'Payment has already been completed.', 'link':'/payments/'}
                return render_to_response('error.html', d, context_instance=RequestContext(request))
            d['pmtId'] = pmt.id # in case of errors, re-post pmtId
        
        if not errors: 
            payer = is_request and otherUser or userNode
            recipient = is_request and userNode or otherUser
            if pmt is None:
                pmt = Payment()  # Create new Payment.
            pmt.payer = payer
            pmt.payer_email = is_request and email or payer.getPrimaryEmail()
            pmt.recipient = recipient
            pmt.recipient_email = is_request and recipient.getPrimaryEmail() or email
            pmt.amount = amount
            pmt.currency = currency
            pmt.date = datetime.now()
            pmt.status = is_request and 'RQ' or 'PE'
            pmt.description = d['description']
            pmt.save()

            if is_request:
                # Send payment request email
                t = template_loader.get_template('emailPmtRequestReceived.txt')
                c = RequestContext(request, {'req': pmt})
                sendEmail("Payment request notification", t.render(c), pmt.payer_email)
                request.session['infos'] = ["Your payment request has been recorded "
                                            "and a notification email sent to the payer."]
                return HttpResponseRedirect('/payments/')
            else:  # Go to payment confirmation page
                return HttpResponseRedirect('/payments/%s/confirm/' % pmt.id)
    
    # present make payment form
    d['infos'] = errors
    if otherUserId: # paying a specific user - URL = payUser/id/
        if Node.objects.filter(pk=otherUserId).count() > 0 and userNode.id != otherUserId:
            d['email'] = Node.objects.get(pk=otherUserId).getPrimaryEmail()
    if pmtId: # editing a pending payment from DB - URL = paymentForm/id/
        if Payment.objects.filter(pk=pmtId).count() > 0:
            pmt = Payment.objects.get(pk=pmtId)
            if pmt.status == 'OK': # can't edit completed payment
                d = {'message':'Payment has already been completed.', 'link':'/payments/'}
                return render_to_response('error.html', d, context_instance=RequestContext(request))
            d['email'] = is_request and pmt.payer_email or pmt.recipient_email
            d['amount'] = pmt.amount
            d['selectedUnitId'] = pmt.currency_id
            d['description'] = pmt.description
            d['pmtId'] = pmtId
    
    d['paymentUnits'] = makeUnitsList(userNode)
    
    # set selected units to account units, if paying account partner, or to default units
    if not d.has_key('selectedUnitId'):
        if otherUserId and userNode.account_set.filter(partner__pk=otherUserId).count() > 0:
            acct = userNode.account_set.filter(partner__pk=otherUserId)[0]
            d['selectedUnitId'] = acct.shared_data.currency_id
        else:
            d['selectedUnitId'] = userNode.display_units_id
    
    d['is_request'] = is_request
    return render_to_response('paymentForm.html', d, context_instance=RequestContext(request))

def makeUnitsList(userNode):
    "Return list of CurrencyUnits available to user to pay/request with."
    accts = userNode.account_set.all()
    acctUnits = []
    for acct in accts:
        unit = acct.shared_data.currency
        if unit not in acctUnits:
            acctUnits.append(unit)
    acctUnits.sort(lambda a, b: cmp(a.long_name, b.long_name))
    
    if userNode.do_conversions: # doing conversions -> pay in any convertible units or account units
        pmtUnits = CurrencyUnit.objects.filter(value__gt=0.0).order_by('long_name')
        hasConvertibleAcct = False
        for unit in pmtUnits: # check that at least one account has convertible units!
            if unit in acctUnits:
                hasConvertibleAcct = True
                break
        if hasConvertibleAcct:
            for unit in acctUnits:
                if unit not in pmtUnits:
                    pmtUnits.append(unit)
        else:
            pmtUnits = acctUnits # no convertible accts, so can pay only in acct units
    else: # no conversions -> only account units
        pmtUnits = acctUnits
    return pmtUnits

def availableCredit(node, unit, incoming=False):
    pmtCurrencyValue = unit.value
    if incoming: # to receive payment, partners must have credit with node
        accts = node.partner_account_set.filter(shared_data__active=True)
    else: # to pay, node must have credit with partners
        accts = node.account_set.filter(shared_data__active=True)

    credit = 0.0
    for acct in accts:
        if acct.getAvailableCredit() > 0.0: # don't add in negative "available credit"
            acctCurrencyValue = acct.shared_data.currency.value
            if node.do_conversions and pmtCurrencyValue and acctCurrencyValue: # do conversion
                credit += acct.getAvailableCredit() * acctCurrencyValue / pmtCurrencyValue
            else: # no conversion
                if acct.shared_data.currency == unit:
                    credit += acct.getAvailableCredit()
    return credit

def confirmPayment(request, pmtId):
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    
    if not Payment.objects.filter(pk=pmtId).count() > 0:
        return HttpResponseRedirect('/payments/')
    
    pmt = Payment.objects.get(pk=pmtId)
    
    if pmt.payer_id != userNode.id:
        return HttpResponseRedirect('/payments/')
    
    if pmt.status != 'PE': # pending
        return HttpResponseRedirect('/payments/')
    
    d = {}
    d['pmt'] = Payment.objects.get(pk=pmtId)
    if d['pmt'].payer_id != userNode.id:
        return HttpResponseRedirect('/payments/')
    return render_to_response('confirmPayment.html', d, context_instance=RequestContext(request))

# this view is set to autocommit below
def pay(request, pmtId):
    """Transfer credit to somebody else's node"""
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=/payments/%s/confirm/' % pmtId)
    
    if not request.POST:
        return HttpResponseRedirect('/payments/')
    
    if not Payment.objects.filter(pk=pmtId).count() > 0:
        return HttpResponseRedirect('/payments/')
    
    pmt = Payment.objects.get(pk=pmtId)
    
    if pmt.payer_id != userNode.id:
        return HttpResponseRedirect('/payments/')
    
    if pmt.status != 'PE': # pending
        return HttpResponseRedirect('/payments/')
    
    # make payment
    maxNodes = 1e20 # infinite - search all nodes
    collisions = 3
    while True: # retry until break or return
        try:
            performPayment(pmt, maxNodes=maxNodes)
            message = "Successfully paid %s %.2f to %s." % (pmt.currency.short_name, pmt.amount, escape(pmt.recipient_email))
            request.session['infos'] = [message]
            sendPaymentEmails(pmt, request)
            break
        except PaymentError, e:
            print e
            if e.retry and collisions > 0: # retry
                collisions -= 1
            else: # quit
                if collisions == 0:
                    request.session['infos'] = ['Credit found, but payment transaction still not able to be committed after four attempts.  May be due to high system activity.']
                else:
                    request.session['infos'] = [e.message]
                if e.retry:
                    request.session['infos'].append('<a href="/payments/%d/edit/">Click here to retry.</a>' % pmt.id)
                elif e.amountLacking <> pmt.amount:
                    request.session['infos'].append('<a href="/payments/%d/edit/">Click here to retry with a smaller amount.</a>' % pmt.id)
                break
    
    return HttpResponseRedirect('/payments/%d/' % pmt.id)

# set payment view to autocommit -- same behaviour as 0.91
# actual payment transaction uses its own db connection
pay = transaction.autocommit(pay)


def cancelPayment(request, pmtId):
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    
    if not Payment.objects.filter(pk=pmtId).count() > 0:
        return HttpResponseRedirect('/payments/')
    
    pmt = Payment.objects.get(pk=pmtId)
    
    if pmt.payer_id != userNode.id:
        return HttpResponseRedirect('/payments/')
    
    if pmt.status not in ('RQ', 'PE'):  # requested, pending
        return HttpResponseRedirect('/payments/')

    if pmt.status == 'RQ':
        pmt.status = 'RF'  # refused
        # *** todo: Send refusal email to requester.
        t = template_loader.get_template('emailPmtRequestRefused.txt')
        c = RequestContext(request, {'req': pmt})
        sendEmail("Payment request refusal notification", t.render(c),
                  pmt.recipient.getPrimaryEmail())
    else:
        pmt.status = 'CA'  # cancelled
    pmt.save()
    request.session['infos'] = ["Payment cancelled."]
    return HttpResponseRedirect('/payments/')
    
# send emails informing payer and recipient of successful payment
def sendPaymentEmails(pmt, request):
    d = {'pmt':pmt}
    
    t = template_loader.get_template('emailPmtSent.txt')
    c = RequestContext(request, d)
    sendEmail("Payment confirmation", t.render(c), pmt.payer_email)
    
    t = template_loader.get_template('emailPmtReceived.txt')
    c = RequestContext(request, d)
    sendEmail("Payment received", t.render(c), pmt.recipient_email)

def paymentList(request):
    d = {}
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    
    d['infos'] = getSessionInfos(request)
    d['userNode'] = userNode
    d['payments'] = Payment.objects.filter(Q(payer=userNode) | Q(recipient=userNode), status='OK').order_by('-date')
    prepPaymentsForDisplay(d['payments'], userNode)
    d['receivedPaymentRequests'] = Payment.objects.filter(payer=userNode, status='RQ'
                                                          ).order_by('-date')
    d['sentPaymentRequests'] = Payment.objects.filter(recipient=userNode, status='RQ'
                                                      ).order_by('-date')

    return render_to_response('paymentList.html', d, context_instance=RequestContext(request))

# for each payment, calculate sign and current value as paid/received (if desired and possible)
def prepPaymentsForDisplay(payments, userNode):
    for pmt in payments:
        pmt.currentValue = 0.0
        if pmt.payer_id == userNode.id: # outgoing payment
            pmt.sign = '-' # paid (negative)
            if userNode.display_units_id and pmt.currency.value:
                for path in pmt.paymentpath_set.all():
                    firstLink = path.paymentlink_set.get(position=1)
                    pmt.currentValue += firstLink.amount * firstLink.payer_account.shared_data.currency.value / userNode.display_units.value
        else: # incoming payment
            pmt.sign = '' # received (positive)
            if userNode.display_units_id and pmt.currency.value:
                for path in pmt.paymentpath_set.all():
                    count = path.paymentlink_set.count()
                    lastLink = path.paymentlink_set.get(position=count)
                    pmt.currentValue += lastLink.amount * lastLink.payer_account.shared_data.currency.value / userNode.display_units.value

def paymentDetail(request, pmtId):
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    
    if Payment.objects.filter(pk=pmtId).count() == 0:
        return HttpResponseRedirect('/summary')
    
    pmt = Payment.objects.get(pk=pmtId)
    if pmt.status != 'OK':
        return HttpResponseRedirect('/summary')
    
    d = {}
    # get any messages from session
    d['infos'] = getSessionInfos(request)
    
    # get every payment link that touches this user
    inLinks = PaymentLink.objects.filter(path__payment=pmtId, payer_account__partner=userNode)
    outLinks = PaymentLink.objects.filter(path__payment=pmtId, payer_account__owner=userNode)
    
    if pmt.payer_id == userNode.id:
        assert outLinks, "User %d is payer for payment %d, but has no outgoing payment links." % (userNode.id, pmt.id)
        d['outPayment'] = True
    elif pmt.recipient_id == userNode.id:
        assert inLinks, "User is %d is recipient for payment %d, but has no incoming payment links." % (userNode.id, pmt.id)
        d['inPayment'] = True
    elif inLinks and outLinks:
        d['thruPayment'] = True
    else: # user should have no links at all
        assert not inLinks and not outLinks, "User %d is an intermediary for payment %d, but does not have both incoming and outgoing links." % (userNode.id, pmt.id)
        return HttpResponseRedirect('/summary')
    
    inAccts = []
    for link in inLinks:
        acct = link.payer_account.get_partner_acct()
        if acct in inAccts: # fetch copy we already have and add to numbers
            acct = inAccts[inAccts.index(acct)]
            acct.inEntry += link.amount
        else:
            acct.inEntry = link.amount
            inAccts.append(acct)
    
    outAccts = []
    for link in outLinks:
        acct = link.payer_account
        if acct in outAccts: # fetch copy we already have and add to numbers
            acct = outAccts[outAccts.index(acct)]
            acct.outEntry += link.amount
        else:
            acct.outEntry = link.amount
            outAccts.append(acct)
    
    d['pmt'] = pmt
    d['inAccts'] = inAccts
    d['outAccts'] = outAccts
    return render_to_response('paymentDetail.html', d, context_instance=RequestContext(request))

def registerIOU(request, otherNodeId=None):
    "For one-hop payments, including account offer and creation if necessary."
    pass


#-------------------- Backend functions -------------------


class PaymentError(Exception):
    def __init__(self, code, message, retry=False, amountLacking=0.0):
        self.code = code
        self.message = message
        self.retry = retry
        self.amountLacking = amountLacking
    def __str__(self):
        return self.message

# entry point
def performPayment(pmt, maxNodes):
    if VERBOSE: print "\nPay %s %.4f from %s to %s:" % (pmt.currency.short_name, pmt.amount, pmt.payer.name, pmt.recipient.name)
    
    graph = PathGraph(pmt, maxNodes)
    available = graph.build()
    if VERBOSE: print "Searched: %d nodes, %d accounts." % (len(graph.visitedNodes), len(graph.sharedAccts))
    if available < pmt.amount:
        pmt.status = 'FA' # failed
        pmt.save()
        raise PaymentError(code=NO_PATH, message="Did not find enough available credit along paths from payer to recipient.  Available: %.2f, needed: %.2f." % (available, pmt.amount), retry=False, amountLacking=pmt.amount-available)

    # this is the transaction
    conn = db_module.connect(DSN) # could get Django's connection here, but would need to turn autocommit off
    cursor = conn.cursor()
    
    cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED;") # psycopg defaults to SERIALIZABLE, but probably don't need that
    
    # first, set payment date to now -- want it as late as possible since it must be later than any updated account to calculate interest properly
    # *** comment these four lines out if doing time travel from testutil.py
    pmtDateSql = "UPDATE ripple_payment SET date = NOW() where id = %d; SELECT date FROM ripple_payment where id = %d;"
    cursor.execute(pmtDateSql, (pmt.id, pmt.id))
    valueRow = cursor.fetchone()
    pmt.date = valueRow[0] # official payment date
    
    paid = 0.0
    try:
        while True:
            path = graph.popPath()
            if path == None: # ran out of paths -- shouldn't happen if single-threaded
                # *** maybe retry here by continuing/restarting search?
                raise PaymentError(code=TX_COLLISION, 
                                                      message="Enough credit found, but it got snatched away by another transaction. \nPayment amount: %.14f\nPaid: %.14f" % (pmt.amount, paid), 
                                                      retry=True, amountLacking=pmt.amount-paid)
            pathAmt = payAlongPath(path=path, amount=pmt.amount - paid, cursor=cursor, pmt=pmt)
            if VERBOSE: print "Paid along path, value %.2f." % pathAmt
            paid += pathAmt
            if round(paid, 12) >= round(pmt.amount, 12) - 5e-12:
                if abs(round(paid, 12) - round(pmt.amount, 12)) < 5e-12: # check rounded to twelve decimals
                    break
                else: # shouldn't happen ever!
                    raise PaymentError(code=OVERPAYMENT, message="*** Serious error. Paid too much! Target amount: %.12f, paid %.12f. Please contact system administrator. ***" % (paid, pmt.amount), retry=False, amountLacking=pmt.amount-paid) # amountLacking will be negative

        # set payment status to OK - not sure if using pmt.save() works here... crashes on my windows machine :)
        cursor.execute("UPDATE ripple_payment SET status = 'OK' WHERE id = %d", (pmt.id,))
        conn.commit()
    except db_module.DatabaseError, detail:
        try:
            print dir(detail)
            conn.rollback()
            pmt.status = 'FA'
            pmt.save()
        except: pass # want to pass on earlier exception, not this one
        raise PaymentError(code=DB_ERROR, message="Payment failed when saving to database: %s" % detail, retry=True)
    except: # any other exception, particularly explicitly-raised PaymentErrors
        try:
            conn.rollback()
            pmt.status = 'FA'
            pmt.save()
        except: pass # want to pass on earlier exception, not this one
        raise # re-raise

    return True

def payAlongPath(path, amount, cursor, pmt):
    # use only transaction-safe DB values - means re-get necessary data
    pathCredit = amount
    
    MULTIPLIER, IOU_LIMIT, BALANCE, INTEREST_RATE, LAST_UPDATE, CURR_VALUE = range(6) # indexes on querySql row
    querySql = "SELECT acct.balance_multiplier, acct.iou_limit, shared.balance, shared.interest_rate, shared.last_update, curr.value \
    FROM ripple_account as acct JOIN ripple_sharedaccountdata as shared ON shared.id = acct.shared_data_id \
    JOIN ripple_currencyunit as curr ON curr.id = shared.currency_id WHERE acct.id = %d"

    valueSql = "SELECT value FROM ripple_currencyunit WHERE id = %d"
    
    # first, get value of pmt currency
    cursor.execute(valueSql, (pmt.currency_id,))
    valueRow = cursor.fetchone()
    pmt.currencyValue = valueRow[0] # value

    # next, get acct info for each acct in path and use to determine path credit
    for acct in path[1:len(path):2]: # accts are at odd indices in path
        # get acct info
        cursor.execute(querySql, (acct.id,))
        queryRow = cursor.fetchone()

        # calculate avail credit (in pmt units)
        acct.actual_balance = queryRow[BALANCE] * queryRow[MULTIPLIER]
        acct.last_update = queryRow[LAST_UPDATE]
        # *** causing errors when only one simultaneous payment happening
        #     this is because of django timezone setting -- unset it?  (works on windows)
        if acct.last_update > pmt.date: # can't properly compute interest if someone else already has since the time this payment was supposed to occur at
            print acct.last_update, pmt.date
            raise PaymentError(code=TX_COLLISION, message="Another transaction updated this account since the time we wanted to pay at.", retry=True)
        acct.interest = computeInterest(acct.actual_balance, queryRow[INTEREST_RATE], acct.last_update, pmt.date)
        acct.eff_balance = acct.actual_balance + acct.interest
        acct.availCredit = queryRow[IOU_LIMIT] + acct.eff_balance

        if pmt.currencyValue: # otherwise, no conversions
            # get acct currency conversion value
            acct.currencyValue = queryRow[CURR_VALUE]

            # calculate available credit in pmt units
            acct.availCredit *= acct.currencyValue / pmt.currencyValue # convert to pmt units
            acct.availCredit = float("%.12f" % acct.availCredit) # round path's amount to 12 decimal places so all paths add exactly to the total payment amount in db

        if acct.availCredit < pathCredit:
            pathCredit = acct.availCredit
            # check that pathCredit doesn't convert back too high, otherwise updating balance may fail
            # **** occasionally causing minute amounts of payment to not go through on predicted number of paths
            # **** instead, allow for minute amounts over limit
            ##if pmt.currencyValue: # only check if we're doing conversions
            ##  roundBack = pathCredit * pmt.currencyValue / acct.currencyValue
            ##  roundBack = float("%.12f" % roundBack)
            ##  if roundBack > pathCredit:
            ##    pathCredit -= 0.000000000001 # twelve digits down, subtract one
    if pathCredit <= 0: return 0 # no credit, no payment along this path

    # insert Path into database
    sql = "INSERT INTO ripple_paymentpath (payment_id, amount) VALUES (%d, %.12f);"
    sql += "SELECT currval('ripple_paymentpath_id_seq');" # at the same time get the ID of the path we just inserted
    cursor.execute(sql, (pmt.id, pathCredit))

    # find ID of path we just inserted
    pathId = cursor.fetchone()[0]

    # make payments
    linkInsSql = "INSERT INTO ripple_paymentlink (path_id, payer_account_id, position, amount, interest, interest_rate) " 
    linkInsSql += "VALUES (%d, %d, %d, %.12f, %.12f, %.10f);"
    ##linkInsSql += "SELECT currval('ripple_paymentlink_id_seq');"
    position = 1 # start link position sequence at 1
    balUpdSql = "UPDATE ripple_sharedaccountdata SET balance = balance - %.14f, last_update = '%s' "
    balUpdSql += "WHERE ripple_sharedaccountdata.id = %d "
    #balUpdSql += "AND last_update = '%s' " # make sure last_update stays consistent, otherwise interest won't work.
    balUpdSql += "AND last_update - '%s' <= INTERVAL '0:0:0.000001' " # alternative version because psycopg sometimes loses a microsecond!
    balUpdSql += "AND balance * %d >= %.14f" # % balance_multiplier, minimum balance needed for payment to succeed
    # makes sure there's enough, even if another transaction has fudged around!
    # above WHERE conditions allow us to use Postgresql in Read Committed (default) mode - see http://www.postgresql.org/files/developer/transactions.pdf
    # *** could do further real-time safety checking on acct.iou_limit too, to be really sure :) ***

    for acct in path[1:len(path):2]:

        # insert PaymentLink
        linkAmount = pathCredit
        if pmt.currencyValue:
            linkAmount *= pmt.currencyValue / acct.currencyValue # convert path amount to acct units
            
        cursor.execute(linkInsSql, (pathId, acct.id, position, linkAmount, -acct.interest, acct.sharedData.interest_rate)) # negative interest because this is an outgoing amount
        if not cursor.rowcount == 1:
            raise PaymentError(code=LINK_INSERT_FAILED, message="Error inserting path link to database.", retry=True) # shouldn't happen
        ##print 'Link %d:' % cursor.fetchone()[0] ###
        ##print '\tAmount: %.14f' % linkAmount
        ##print '\tBalance: %.14f -> %.14f' % (acct.actual_balance, acct.actual_balance - (linkAmount - acct.interest))
        ##print '\tInterest: %.14f' % -acct.interest
        position = position + 1

        # update SharedAccountData balance
        # **** 10e-12 = allow for a minute amount over limit due to rounding error in conversion
        balChange = linkAmount - acct.interest
        cursor.execute(balUpdSql, (balChange * acct.balance_multiplier, pmt.date, acct.shared_data_id, 
                                                              acct.last_update, acct.balance_multiplier, balChange - acct.iou_limit - 10e-12))
        if not cursor.rowcount == 1:
            shared = SharedAccountData.objects.get(pk=acct.shared_data_id) # find out actual balance, last_update in db
            raise PaymentError(code=BAL_UPDATE_FAILED, # happens if sql conditions fail, great for concurrent transactions!
                message="Error updating account balance in database. SQL: " + \
                balUpdSql % (balChange * acct.balance_multiplier, str(pmt.date), acct.shared_data_id, acct.last_update, \
                acct.balance_multiplier, balChange - acct.iou_limit - 1e-12) + \
                "\nActual balance: %.14f (expected: %.14f)\nIOU limit: %.2f\nLast update: %s (expected %s)" % \
                (shared.balance, acct.actual_balance * acct.balance_multiplier, acct.iou_limit, shared.last_update, acct.last_update),
                retry=True)

    return pathCredit


"""
    def getAvgSteps(self):
        count = 0
        for stub in self.fwdStubs:
            count += len(stub) / 2
        for stub in self.bwdStubs:
            count += len(stub) / 2
        return float(count) / (len(self.fwdStubs) + len(self.bwdStubs))
"""
