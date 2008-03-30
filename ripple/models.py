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

from django.db import models

import sha
from datetime import datetime

#todo: validators?
#todo: add admin tags, default values, etc. - nice model things
#todo: split Node up into User and Node with 1-1 relationship to speed up node fetching??

DIGITS = 24 # max. number of digits in amounts
DECIMALS = 12 # digits reserved for decimals

class CurrencyUnit(models.Model):
    short_name = models.CharField(max_length=5, unique=True)
    long_name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=3)
    value = models.DecimalField(max_digits=DIGITS, decimal_places=DECIMALS, default=0.0) # in base units - for conversion
    last_update = models.DateTimeField(auto_now=True) # last value update
    
    class Admin:
        list_display = ('long_name', 'short_name', 'symbol', 'value', 'last_update')
    
    class Meta:
        ordering = ('short_name',)
    
    def __str__(self):
        return self.short_name


class Node(models.Model):
    username = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=50)
    pwd = models.CharField(max_length=40)
    salt = models.CharField(max_length=10, default='') # for salting the password before hashing
    display_units = models.ForeignKey(CurrencyUnit, null=True, blank=True, default=None)
    do_conversions = models.BooleanField(default=True) # allow conversion on through payments
    #notify_emails = models.BooleanField()
    #bulletins = models.BooleanField()
    location = models.DecimalField(max_digits=12, decimal_places=11) # routing location

    class Admin:
        list_display = ('username', 'name', 'display_units', 'do_conversions')
        list_filter = ('display_units', 'do_conversions')
        search_fields = ('username', 'name')
    
    def __str__(self):
        return self.name or self.username
    
    def checkPwd(self, pwd):
        if self.pwd == sha.new(pwd + self.salt).hexdigest():
            return True
        else: return False
    
    def setPwd(self, pwd):
        self.pwd = sha.new(pwd + self.salt).hexdigest()
    
    def getPrimaryEmail(self):
        return self.emailaddr_set.get(primary__exact=True).email


class EmailAddr(models.Model):
    node = models.ForeignKey(Node, db_index=True)
    email = models.EmailField(unique=True)
    code = models.CharField(max_length=10, unique=True)
    confirmed = models.BooleanField(default=False)
    primary = models.BooleanField()
    
    class Admin:
        list_display = ('email', 'node', 'confirmed', 'primary')
        list_filter = ('confirmed', 'primary')
        search_fields = ('email',)

    def __str__(self):
        return self.email


class Reminder(models.Model):
    node = models.ForeignKey(Node)
    code = models.CharField(max_length=10, unique=True)
    date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return "%s %s" % (self.node, self.date)

    class Admin:
        list_display = ('node', 'code', 'date')


# accounts ----------------------------------
class SharedAccountData(models.Model):
    currency = models.ForeignKey(CurrencyUnit)
    balance = models.DecimalField(max_digits=DIGITS, decimal_places=DECIMALS)
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    
    # interest
    interest_rate = models.DecimalField(max_digits=13, decimal_places=10, default=0.0) # stored as decimal (as opposed to percentage for display)
    proposed_rate = models.DecimalField(max_digits=13, decimal_places=10, null=True, blank=True, default=None)
    node_to_confirm = models.ForeignKey(Node, related_name='shared_accounts_to_confirm', null=True, blank=True, default=None)
    last_update = models.DateTimeField(auto_now_add=True) # to quickly compute present interest tally during payments
    # (interest is added to balance each update, ie, each transaction)

    class Admin:
        list_display = ('currency', 'balance', 'active', 'interest_rate', 'last_update')
        list_filter = ('currency', 'active')
    
    def __str__(self):
        str = '%s account %d' % (self.currency, self.id)
        if not self.active:
            str += " (inactive)"
        return str
    
    def displayRate(self):
        return self.interest_rate * 100.0
    def displayProposedRate(self):
        if self.proposed_rate <> None:
            return self.proposed_rate * 100.0
        return None
    
    # avoid rounding on save when django converts to string for SQL command
    def save(self):
        if type(self.balance) == float:
            self.balance = '%.12f' % self.balance
        super(SharedAccountData, self).save()
        self.balance = float(self.balance)

class Account(models.Model):
    owner = models.ForeignKey(Node, db_index=True)
    partner = models.ForeignKey(Node, related_name='partner_account_set', db_index=True)
    shared_data = models.ForeignKey(SharedAccountData)
    balance_multiplier = models.IntegerField(choices=[(1, '+1'), ( -1, '-1')])
    #partner_acct = models.ForeignKey("self", null=True, blank=True)

    # what owner calls the account (default would be name/email of partner)
    name = models.CharField(max_length=50)

    # current max negative (debt) balance of this account
    iou_limit = models.DecimalField(max_digits=DIGITS, decimal_places=DECIMALS)

    # meta-limits - acceptable range for upper and lower account limits according to owner
    # used to allow each partner to regulate their own credit flexibly
    # iou_limit = min(my_limit, partner_acct.partner_limit)
    partner_limit = models.DecimalField(max_digits=DIGITS, decimal_places=DECIMALS) # max amt to accept from partner
    my_limit = models.DecimalField(max_digits=DIGITS, decimal_places=DECIMALS, null=True, blank=True) # max amt of debt to owe to partner - null -> no limit

    class Admin:
        list_display = ('id', 'name', 'owner', 'shared_data', 'iou_limit', 'partner_limit', 'my_limit')
        search_fields = ('name', 'owner__name', 'owner__username', 'partner__name', 'partner__username')

    def __str__(self):
        return '%s\'s view of %s, "%s"' % (self.owner, self.shared_data, self.name)

    def get_partner_acct(self):
        return Account.objects.get(shared_data__pk=self.shared_data_id, owner__pk=self.partner_id)
    
    def getAvailableCredit(self):
        return self.iou_limit + self.getBalance() #- frozen

    def getBalance(self):
        return self.getBalanceNoInterest() + self.getPresentInterest()

    def getBalanceNoInterest(self):
        return self.shared_data.balance * self.balance_multiplier

    def getPresentInterest(self):
        from ripplesite.ripple.views.pathgraph import computeInterest
        return computeInterest(self.getBalanceNoInterest(), self.shared_data.interest_rate, self.shared_data.last_update, datetime.now())


class Offer(models.Model):
    initiator = models.ForeignKey(Node, related_name='sent_offer_set')
    recipient_email = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=DIGITS, decimal_places=DECIMALS)
    currency = models.ForeignKey(CurrencyUnit)
    initial_balance = models.DecimalField(max_digits=DIGITS, decimal_places=DECIMALS, default=0.0)
    interest_rate = models.DecimalField(max_digits=13, decimal_places=8) # stored as percentage, 2 fewer decimals

    class Admin:
        list_display = ('initiator', 'recipient_email', 'amount', 'currency', 'initial_balance')
        list_filter = ('currency',)
        search_fields = ('initiator__name', 'initiator__username', 'recipient_email')

    def __str__(self):
        return "%s offer %s %.2f to %s" % (self.initiator, self.currency, self.amount, self.recipient_email)


# payments ---------------------------
PAYMENT_STATUS_CHOICES = (
    ('RQ', 'Requested'),
    ('PE', 'Pending'),
    ('OK', 'Completed'),
    ('CA', 'Cancelled'),
    ('RF', 'Refused'),
    ('FA', 'Failed'),
)

class Payment(models.Model):
    payer = models.ForeignKey(Node, related_name='outgoing_payment_set', db_index=True)
    payer_email = models.EmailField()
    recipient = models.ForeignKey(Node, related_name='incoming_payment_set', db_index=True)
    recipient_email = models.EmailField()
    date = models.DateTimeField(auto_now_add=True)
    currency = models.ForeignKey(CurrencyUnit)
    amount = models.DecimalField(max_digits=DIGITS, decimal_places=DECIMALS)
    status = models.CharField(max_length=2, choices=PAYMENT_STATUS_CHOICES)
    description = models.TextField(default='', blank=True)

    def __str__(self):
        return "%d: %s pay %s %.2f to %s" % (self.id, self.payer, self.currency, self.amount, self.recipient)

    class Admin:
        list_display = ('id', 'payer', 'recipient', 'date', 'currency', 'amount', 'status')
        list_filter = ('currency', 'status')
        search_fields = ('payer__name', 'payer__username', 'payer_email', 'recipient__name', 'recipient__username', 'recipient_email', 'description')
    
    # avoid rounding on save when django converts to string for SQL command
    def save(self):
        if type(self.amount) == float:
            self.amount = '%.12f' % self.amount
        super(Payment, self).save()
        self.amount = float(self.amount)
        

# payment may have multiple paths
class PaymentPath(models.Model):
    payment = models.ForeignKey(Payment)
    amount = models.DecimalField(max_digits=DIGITS, decimal_places=DECIMALS)

    def __str__(self):
        return "%d: %.2f on payment %s" % (self.id, self.amount, self.payment)
    
    # avoid rounding on save when django converts to string for SQL command
    def save(self):
        if type(self.amount) == float:
            self.amount = '%.12f' % self.amount
        super(PaymentPath, self).save()
        self.amount = float(self.amount)


# each link is an account from the perspective of the partner closest to payment recipient
# (the IOU recipient for this link)
class PaymentLink(models.Model):
    path = models.ForeignKey(PaymentPath)
    payer_account = models.ForeignKey(Account)
    position = models.PositiveIntegerField() # position in path sequence, starting at 1

    # needed because this account may be in a different currency than payment
    amount = models.DecimalField(max_digits=DIGITS, decimal_places=DECIMALS)
    interest = models.DecimalField(max_digits=DIGITS, decimal_places=DECIMALS) # add this to amount to get amount actually subtracted from acct balance during transaction
    interest_rate = models.DecimalField(max_digits=13, decimal_places=10) # for auditability

    def __str__(self):
        return "%d. %s on path %s" % (self.position, self.payer_account, self.path)
    
    # avoid rounding on save when django converts to string for SQL command
    def save(self):
        if type(self.amount) == float:
            self.amount = '%.12f' % self.amount
        if type(self.interest) == float:
            self.interest = '%.12f' % self.interest
        super(PaymentLink, self).save()
        self.amount = float(self.amount)
        self.interest = float(self.interest)

