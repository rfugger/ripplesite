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
Ripple back-end test module

- put in views directory
- set environment variable DJANGO_SETTINGS_MODULE=ripple.settings
- run this script
- comment out the populate database parts and run again to continue testing payments
"""

from ripplesite.ripple.models import *
from ripplesite.ripple.views import makeConfirmationCode
import routing, payment, netgen, random, time
from django.db import connection
from pathgraph import computeInterest

from datetime import datetime, timedelta


ERROR = 100e-12 # allowable rounding error on integrity checks

def addNode(username, realname, email=None, unit_name=None):
    node = Node(username=username, name=realname.title(), location=routing.getNewLocation())
    node.setPwd(username)
    if unit_name:
        node.display_units = getCurrency(unit_name)
    node.save()
    if email is None:
        email = "%s@r.com" % username
    emailaddr = EmailAddr(node=node, email=email, code=makeConfirmationCode(), confirmed=True, primary=True)
    emailaddr.save()
    return node

def getNode(name):
    return Node.objects.get(username=name)

def addCurrency(shortname, symbol='$', longname='', value=0):
    c = CurrencyUnit(short_name=shortname, long_name=longname, symbol=symbol, value=value)
    c.save()
    return c

def getCurrency(shortname):
    return CurrencyUnit.objects.get(short_name=shortname)

# adds pair of accts between nodes, and shared data object
def addAccts(node1name, node2name, credit, reverse_credit=None, currencyname='CAD', interest=0.0, timeTravelDate=None):
    node1 = getNode(node1name)
    node2 = getNode(node2name)
    currency = getCurrency(currencyname)
    if reverse_credit == None:
        reverse_credit = credit
    shared = SharedAccountData(currency=currency, balance=0, interest_rate=interest)
    shared.save()
    
    if timeTravelDate:
        shared.created = timeTravelDate
        shared.last_udpate = timeTravelDate
        shared.save()

    acct1 = Account(owner=node1, partner=node2, shared_data=shared, balance_multiplier=1, iou_limit=reverse_credit, partner_limit=credit, name=node2.name)
    acct1.save()
    acct2 = Account(owner=node2, partner=node1, shared_data=shared, balance_multiplier=-1, iou_limit=credit, partner_limit=reverse_credit, name=node1.name)
    acct2.save()
    return acct1, acct2

# returns names of connected nodes
def getConnections(name):
    return [acct.partner.username for acct in getNode(name).account_set.all()]

def pay(payername, recipientname, amount, currencyname='CAD'):
    payer = getNode(payername)
    recipient = getNode(recipientname)
    currency = getCurrency(currencyname)
    amount = float("%.2f" % amount)
    pmt = Payment(payer=payer, payer_email=payer.getPrimaryEmail(), recipient=recipient, recipient_email=recipient.getPrimaryEmail(), amount=amount, currency=currency, status='PE', description='')
    pmt.save()
    payment.pay(pmt)
    return pmt


# delete account, its partner account, and their shared data
def deleteAcct(acct):
    shared = acct.shared_data
    partner = acct.get_partner_acct()
    acct.partner_acct_id = None # avoid illegal foreign key
    acct.save()
    partner.delete()
    acct.delete()
    shared.delete()

def deleteNode(name):
    node = getNode(name)
    accts = node.partner_account_set.all()
    for acct in accts:
        deleteAcct(acct)
    for email in node.emailaddr_set():
        email.delete()
    node.delete()

def deleteAllNodes():
    print "Deleting all nodes in database."
    cursor = connection.cursor()
    cursor.execute('delete from ripple_account;')
    cursor.execute('delete from ripple_sharedaccountdata;')
    cursor.execute('delete from ripple_emailaddr;')
    cursor.execute('delete from ripple_node;')

def clearPayments():
    print "Clearing all payments from database."
    cursor = connection.cursor()
    cursor.execute('delete from ripple_paymentlink;')
    cursor.execute('delete from ripple_paymentpath;')
    cursor.execute('delete from ripple_payment;')
    for shared in SharedAccountData.objects.all():
        shared.balance = 0.0
        shared.last_update = shared.created
        shared.save()

def cleardb():
    clearPayments()
    deleteAllNodes()

# build random graph - erases old network!
# avg_conn = avg number of connections per node
# pref_coeff = number between 0-1, tendency to connect to nodes that have many connections
def populate(num_nodes, avg_conn, pref_coeff, avg_credit=100, seed=None, timeTravel=None):
    if seed:
        random.seed(seed)
    cleardb()
    timeTravelDate = None
    if timeTravel:
        timeTravelDate = datetime.now() - timedelta(timeTravel) # number of days
    print "Populating database with %d nodes." % num_nodes
    for i in range(0, num_nodes):
        addNode(str(i))
    acctList = netgen.generate(num_nodes, avg_conn, pref_coeff, seed)
    currencyList = CurrencyUnit.objects.all()
    for acct in acctList:
        amount = 0
        rand_avg = avg_credit / 10
        while True:
            amount += 10 * random.randint(1,rand_avg)
            if random.random() < .50: break
        reverseAmount = amount
        if random.random() < .50: # occasionally have a different reverse amount
            reverseAmount += 10 * random.randint(-rand_avg,rand_avg)
        reverseAmount = max(reverseAmount, 0)
        currencyName = currencyList[random.randint(0, len(currencyList) - 1)].short_name
        interest = 0.0
        if random.random() < .5: # half the time have interest
            interest = random.randint(0, 100) / 1000.0 # 0.0-0.1 in increments of 0.001
        addAccts(acct[0], acct[1], amount, reverseAmount, currencyName, interest, timeTravelDate=timeTravelDate)


def simulate(num_payments, avg_amount=100, seed=None, timeTravel=None):
    if seed:
        random.seed(seed)
    if timeTravel:
        timeTravel = datetime.now() - timedelta(timeTravel) # number of days
    nodeIds = [x['id'] for x in Node.objects.values('id')]
    currencyList = CurrencyUnit.objects.all()
    pmts = []
    for i in range(num_payments): # generate all payments first to avoid interference in seeded random-number generation
        payerId = nodeIds[random.randint(0, len(nodeIds) - 1)]
        while True:
            recipientId = nodeIds[random.randint(0, len(nodeIds) - 1)]
            if recipientId != payerId: break
        amount = 0.0
        while True:
            amount += random.random() * avg_amount
            if random.random() < .50: break
        currency = random.choice(currencyList)
        pmts.append((payerId, recipientId, amount, currency))
    
    startTime = time.clock()
    succeeded = 0
    tried = 0
    pmtDate = timeTravel
    for pmt_data in pmts:
        tried += 1
        pmt = Payment(payer_id=pmt_data[0], recipient_id=pmt_data[1], amount=pmt_data[2], currency=pmt_data[3], status='PE')
        pmt.save() # rounds to 12 sig figs.
        if pmtDate:
            pmtDate += timeTravelStep(pmtDate, datetime.now(), num_payments - tried + 1)
            pmt.date = pmtDate
            pmt.save()
        #pmt = Payment.objects.get(pk=pmt.id) # *** hack to fix django bugs where auto-added date doesn't get set on object after save and amount gets rounded
        
        # make payment
        print "\n%d. Attempting to pay %s%.4f from %s to %s." % (tried, pmt.currency.symbol, pmt.amount, pmt.payer, pmt.recipient)
        maxNodes = 1e20 # infinite - search all nodes
        collisions = 3
        while True: # retry until break or return
            try:
                payment.performPayment(pmt, maxNodes=maxNodes)
                succeeded += 1
                print "Payment completed."
                for path in pmt.paymentpath_set.all():
                    print " - %s%.4f along %d-hop path" % (pmt.currency.symbol, path.amount, path.paymentlink_set.count())
                break
            except payment.PaymentError, e:
                if e.code in (payment.TX_COLLISION, payment.BAL_UPDATE_FAILED, payment.DB_ERROR) and collisions > 0: # retry if path found but got snatched away
                    print e
                    print '\nRetry %d...' % (4 - collisions)
                    collisions -= 1
                else: # quit
                    print e
                    print '\nGiving up.'
                    break
    
    totalTime = time.clock() - startTime
    print "%d successful out of %d payments processed in %d:%02d" % (succeeded, num_payments, totalTime / 60, totalTime % 60)
    print "Average: %.1f seconds per payment." % (totalTime / num_payments)


def timeTravelStep(start_date, end_date, num_payments):
    delta = end_date - start_date
    divisor = num_payments + random.randint(0, num_payments)
    while random.random() < 0.5:
        divisor += random.randint(0, num_payments)
    return delta / divisor


# makes sure accounts balance with payments
def testIntegrity(checkPayments=True):
    
    if checkPayments:
        testPaymentIntegrity()
    testAccountIntegrity()
    
    print "Database integrity check complete."
    

def testPaymentIntegrity():
    for payment in Payment.objects.filter(status='OK'):
        pathSum = 0
        for path in PaymentPath.objects.filter(payment=payment):
            pathSum += path.amount
            nodeId = payment.payer_id
            linkCount = 0
            prevLink = None
            while nodeId != payment.recipient_id:
                linkCount += 1
                link = PaymentLink.objects.get(path=path, position=linkCount)
                if link == None:
                    print "Payment %d, Path %d: missing Link in position %d" % (payment.id, path.id, linkCount)
                # check that previous link points to same node that this link starts from
                if nodeId != link.payer_account.owner_id:
                    print "Payment %d, Path %d: Links don't match up to a single node at position %d" % (payment.id, path.id, linkCount)
                if prevLink:
                    # check that conversions don't happen at nodes that have do_conversions == False
                    if not Node.objects.get(pk=nodeId).do_conversions:
                        if link.payer_account.shared_data.currency_id != prevLink.payer_account.shared_data.currency_id:
                            print "Payment %d, Path %d: invalid conversion at node %d, position %d" % (payment.id, path.id, nodeId, linkCount)
                nodeId = link.payer_account.partner_id
                prevLink = link
            if linkCount != PaymentLink.objects.filter(path=path).count():
                print "Payment %d, Path %d: too many links in DB" % (payment.id, path.id)
        if abs(pathSum - payment.amount) > ERROR:
            print "Payment %d: paths don't sum (should be %.12f, is %.12f)" % (payment.id, payment.amount, pathSum)

def testAccountIntegrity():
    for shared in SharedAccountData.objects.all():
        #print "\n*** %s ***" % shared
        acctCurrency = shared.currency
        fwdAcct = Account.objects.get(shared_data=shared, balance_multiplier=1)
        bwdAcct = Account.objects.get(shared_data=shared, balance_multiplier=-1)
        
        if fwdAcct.getBalanceNoInterest() < -fwdAcct.iou_limit - ERROR:
            print 'Account %d over limit: Balance %.12f, Limit %.12f.' % \
                (fwdAcct.id, fwdAcct.getBalanceNoInterest(), -fwdAcct.iou_limit)
        if bwdAcct.getBalanceNoInterest() < -bwdAcct.iou_limit - ERROR:
            print 'Account %d over limit: Balance %.12f, Limit %.12f.' % \
                (bwdAcct.id, bwdAcct.getBalanceNoInterest(), -bwdAcct.iou_limit)
        
        tally = 0.0
        last_date = None
        for link in PaymentLink.objects.filter(payer_account__id__in=(fwdAcct.id, bwdAcct.id)
                                                                      ).extra(select={'date': 'pmt.date'},
                                                                                      tables=('ripple_payment as pmt', 'ripple_paymentpath as path'),
                                                                                      where=('path.payment_id=pmt.id', 'path.id=ripple_paymentlink.path_id')
                                                                      ).order_by('date', 'id'):
            path = link.path
            payment = path.payment
            acct = link.payer_account
            #print "%d: %.12f (%.12f/%.3f) on %s = %.12f" % \
            #  (link.id, link.amount, link.interest, link.interest_rate, payment.date, tally)
            interest = 0.0
            if last_date: # skip first transaction on account because balance/interest are zero
                pathAmount = path.amount 
                if acctCurrency.value:
                    pathAmount *= payment.currency.value / acctCurrency.value
                interest = computeInterest(tally * acct.balance_multiplier, link.interest_rate, last_date, payment.date)
                if abs(interest + link.interest) > .5e-12: # should be exact, not sure why sometimes get errors here
                    print "Link %d: incorrect interest.\n\tBalance: %.14f.\n\tCorrect value: %.20f\n\tRecorded %.12f" % \
                        (link.id, tally, interest, -link.interest)
                
                if abs(pathAmount - link.amount) > 1e-12:
                    print "Link %d: incorrect amount. Correct value: %.20f, recorded %.12f" % \
                        (link.id, pathAmount, link.amount)
            else:
                if link.interest != 0.0:
                    print "Link %d: first transaction interest not zero.  (%.12f)" % (link.id, link.interest)
            
            last_date = payment.date
            tally -= (link.amount + link.interest) * acct.balance_multiplier
        
        if abs(tally - shared.balance) > ERROR: # sometimes this is not quite exact either, maybe due to summing rouding errors?
            print 'Shared account %d doesn\'t balance with transaction total.  Balance: %.12f, Transactions: %.12f.' % \
                (shared.id, shared.balance, tally)
    
    
def resetLocations():
    for node in Node.objects.all():
        node.location = routing.getNewLocation()
        node.save()

#----- test runs ---------------------------------------


## Steps: 
## 1. first step on a fresh database - only do once.
##----------------------------------
def addCurrencies():
    
    addCurrency('USD', '$', 'US Dollar', 1.0)
    addCurrency('CAD', '$', 'Canadian Dollar', 0.8)
    addCurrency('GBP', 'L', 'British Pound', 2.0) # '\xa3'
    addCurrency('EUR', 'E', 'Euro', 1.5) # '\x80'
    addCurrency('HRS', 'hr', 'Hour', 0.0)
    
    
## 2. populate database and shuffle the nodes
## - edit populate parameters to change nature of database
## - maybe try shuffling a few more times, although 10x the number of nodes seems to be enough
## - when replacing a database that has a lot of nodes, faster to drop tables and reinstall with django-admin first
## - compare payment speed with and without shuffling
##---------------------------------
def addNodes():
    
    populate(num_nodes=100, avg_conn=10, pref_coeff=.8, avg_credit=1000, timeTravel=None)
    circle = routing.Circle()
    print "Product of connection lengths before (log scale):", circle.getDistProduct()
    print circle.shuffle(10000), "switches."
    print "Product of connection lengths after (log scale):", circle.getDistProduct()
    
    
## 3. test runs - run repeatedly by commenting out other sections after the first time
## - edit simulate parameters to run more payments, or try bigger amounts
##-----------------------------  
def run():
    clearPayments() # start with all balances zero - optional
    simulate(num_payments=1000, avg_amount=100, timeTravel=None) # *** be sure to comment out lines in payment.performPayment when enabling time travel!
    testIntegrity(checkPayments=False) # optional
    

def test():
    testIntegrity(checkPayments=False)

def clear():
    clearPayments()

# todo: add more arguments to command line
if __name__ == '__main__':
    import sys
    
    help = 'args: addcurrencies|addnodes|run|test|clear'
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'addcurrencies':
            addCurrencies()
        elif sys.argv[1] == 'addnodes':
            addNodes()
        elif sys.argv[1] == 'run':
            run()
        elif sys.argv[1] == 'test':
            test()
        elif sys.argv[1] == 'clear':
            clear()
        else:
            print help
    else:
        print help
    
