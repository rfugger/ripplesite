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
path search module

search depth first by best direction determined by MH locations.
"""

#todo: optimize by using custom node and account objects that only hold data we actually use here
#todo: prioritize directions by (available credit / distance) instead of just distance?
#todo: maxDepth parameter to search?

from django.conf import settings
import routing
import math, calendar
from datetime import datetime

VERBOSE = settings.DEBUG

# path finding nuts and bolts
class PathGraph:

    def __init__(self, pmt, maxNodes):
        self.pmt = pmt
        self.maxNodes = maxNodes
        self.payer = pmt.payer
        self.recipient = pmt.recipient
        self.paths = []
        self.visitedNodes = {}
        self.sharedAccts = {}
        self.credit = 0.0

    def build(self):
        ##self.search(self.payer, self.pmt.amount * 1.00001, path=[])
        self.search(self.payer, self.pmt.amount, path=[])
        if VERBOSE: print "Total found: %.2f." % self.credit
        
        # sort paths by amount (located at end of each path)
        # self.paths.sort(amount_cmp) # *** can cause failure unless only found amounts are used per path
        return self.credit
    
    # recursive searcher
    def search(self, node, amount, path):
        # base case: recipient reached
        if node.id == self.recipient.id:
            path += [self.recipient, amount] # append amount to path for later sorting
            self.paths.append(path)
            if VERBOSE: print "Found path with %.2f credit." % amount
            #if VERBOSE: print [node.id for node in path[0:-1:2]]
            self.credit += amount
            for acct in path[1:-2:2]: # add to usedCredit
                acct.sharedData.usedCredit += amount * acct.balance_multiplier
            return amount
        
        # base case: max nodes searched
        if len(self.visitedNodes) >= self.maxNodes:
            print "Max nodes searched, giving up."
            return 0.0
        
        # retrieve/initialize node data
        if node.id in self.visitedNodes:
            node = self.visitedNodes[node.id]
        else:
            self.visitedNodes[node.id] = node
            node.exhausted = False
            # *** query - main one to optimize
            if self.pmt.currency.value and node.do_conversions: # can only convert acct if pmt currency can convert
                node.accts = node.account_set.filter(shared_data__currency__value__gt=0.0, shared_data__active=True) # only check accts that can be converted to pmt units
            else:
                node.accts = node.account_set.filter(shared_data__currency__pk=self.pmt.currency_id, shared_data__active=True) # only check accts that have same units as previous step
        
        for acct in node.accts: # initialize account data
            acct.partnerNode = acct.partner # *** query - all new nodes come from here
            
            if acct.shared_data_id in self.sharedAccts:
                acct.sharedData = self.sharedAccts[acct.shared_data_id]
            else:
                acct.sharedData = acct.shared_data # *** query
                acct.sharedData.usedCredit = 0.0 # using credit on one account affects them both, so keep track
                acct.sharedData.interest = computeInterest(acct.sharedData.balance, acct.sharedData.interest_rate, acct.sharedData.last_update, self.pmt.date) 
                self.sharedAccts[acct.sharedData.id] = acct.sharedData
            
            acct.availCredit = acct.iou_limit + acct.balance_multiplier * (acct.sharedData.balance + acct.sharedData.interest)
            if self.pmt.currency.value: # do conversion
                acct.availCredit *= acct.sharedData.currency.value / self.pmt.currency.value # convert to pmt units
            acct.availCredit -= acct.balance_multiplier * acct.sharedData.usedCredit
            
            # hacks for passing extra params to built-in python sort comparison function
            acct.recipLocation = self.recipient.location
            acct.usableCredit = min(acct.availCredit, amount)
        
        # sort accounts by routing priority (defined below in routing_cmp)
        node.accts = list(node.accts)
        node.accts.sort(routing_cmp)
        
        foundCredit = 0.0
        for acct in node.accts: # go through accts one at a time, searching
            if acct.partnerNode.id in self.visitedNodes: # pick up whether partner is exhausted
                if self.visitedNodes[acct.partnerNode.id].exhausted:
                    if VERBOSE: print "Node %s exhausted, ignoring." % acct.partnerNode.username
                    continue
            
            # recursive step
            if acct.availCredit > 0.0 and acct.partnerNode not in path: # no loops
                newAmount = min(amount - foundCredit, acct.availCredit)
                foundCredit += self.search(acct.partnerNode, newAmount, path + [node, acct])
                if foundCredit >= amount or len(self.visitedNodes) > self.maxNodes:
                    return foundCredit
        
        if foundCredit < amount:
            node.exhausted = True
        
        return foundCredit

    # only called after graph is built - pops highest-amount path
    def popPath(self):
        if len(self.paths) > 0:
            path = self.paths.pop(0)
            if VERBOSE: print "Popping path, value %.2f." % path[-1]
            return path[:-1] # trim off amount on end
        else:
            return None

class HopLimitReached(Exception):
    def __init__(self, found):
        self.found = found

# for sorting paths
def amount_cmp(path1, path2):
    if path1[-1] > path2[-1]:
        return -1
    elif path1[-1] == path2[-1]:
        return 0
    else:
        return 1

# for sorting accounts
def routing_cmp(acct1, acct2):
    try:
        score1 = acct1.usableCredit / routing.getDistance(acct1.partnerNode.location, acct1.recipLocation)
    except ZeroDivisionError:
        return -1 # acct1 goes to recipient, so it should go before
    
    try:
        score2 = acct2.usableCredit / routing.getDistance(acct2.partnerNode.location, acct2.recipLocation)
    except ZeroDivisionError:
        return 1 # acct2 goes to recipient, so acct1 should go after
    
    if score1 > score2:
        return -1 # acct1 better, goes before
    else:
        return 1 # acct2 better, acct1 goes after


# interest computing functions
def computeInterest(p, rate, start_date, end_date):
    if rate == 0.0: # should be most common case
        return 0.0

    tally = 0.0
    last_date = start_date
    for year in range(start_date.year, end_date.year): # treat each year in range separately
        end_of_year = datetime(year + 1, 1, 1) # midnight of Jan. 1st
        tally += computeInterestWithinYear(p, rate, end_of_year - last_date, daysInYear(year))
        last_date = end_of_year

    tally += computeInterestWithinYear(p, rate, end_date - last_date, daysInYear(end_date.year))
    return tally

def daysInYear(year):
    if calendar.isleap(year):
        return 366.0
    else:
        return 365.0

def computeInterestWithinYear(p, rate, delta, year_days=365.0): 
    days = delta.days + delta.seconds / 86400.0 + delta.microseconds / 86400e6
    return p * (math.exp(rate * days / year_days) - 1.0)


