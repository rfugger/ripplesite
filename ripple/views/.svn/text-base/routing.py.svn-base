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
Ripple routing module

#todo: Use sampling to estimate improvements with shuffling
"""

import random, math
import psycopg as db_module # *** change 'psycopg' to 'MySQLdb' for MySQL
from ripplesite.ripple.models import Node
from django.conf import settings

from dbconnect import DSN

# using locations from -pi to pi on the unit circle
# using integers over the full range was overflowing when casting to floats on some kleinberg calculations
LOCATION_MAX = 3.1415926535897931

def getDistance(pos1, pos2):
    dist = abs(pos1 - pos2)
    if dist > LOCATION_MAX:
        dist = 2 * LOCATION_MAX - dist
    return dist

# new, unused random location for new nodes
def getNewLocation():
    while True:
        newLoc = (random.random() * 2 - 1) * LOCATION_MAX
        if Node.objects.filter(location=newLoc).count() == 0:
            break
    return newLoc

# class for doing mass shuffle of all nodes quickly
class Circle:
    def __init__(self):
        # get all node ids and locations and store
        self.shuffleNodes = {} # stores node, location, partners, and current product of distances to partners by node ID
        self.nodeIds = [] # assign an index position to each node ID for random selection
        for node in Node.objects.values('id', 'location'):
            shuffleNode = ShuffleNode(node['id'], node['location'])
            self.shuffleNodes[shuffleNode.id] = shuffleNode
            self.nodeIds.append(shuffleNode.id)

        # connect to partners and initialize distProducts
        for nodeId in self.shuffleNodes:
            node = self.shuffleNodes[nodeId]
            partnerIds = Node.objects.extra(tables=['ripple_account'], # extra table needed for query (other than nodes)
                                                                            where=['ripple_account.owner_id = %d',
                                                                                          'ripple_node.id = ripple_account.partner_id'],
                                                                            params=[nodeId]).values('id')
            node.partners = []
            node.distProduct = 1.0
            for partnerId in partnerIds:
                partner = self.shuffleNodes[partnerId['id']]
                node.partners.append(partner)
                node.distProduct *= getDistance(node.location, partner.location)

    # try n location swaps and save new locations to database
    #todo: rewrite with explicit queries for better efficiency & transactions for safety?
    def shuffle(self, n, seed=-1):
        if seed != -1:
            random.seed(seed)
        switches = 0
        count = 0
        while count < n:
            count += 1
            # pick two random nodes
            n1 = random.randint(0, len(self.nodeIds) - 1)
            if self.swap(n1):
                switches += 1
        self.save()
        return switches

    # test-swap locations: nodeId against another random node
    # returns True if locations switched, False if not
    def swap(self, nodeId):
        n1 = nodeId
        while True:
            n2 = random.randint(0, len(self.nodeIds) - 1)
            if n2 != n1: break

        node1 = self.shuffleNodes[self.nodeIds[n1]]
        node2 = self.shuffleNodes[self.nodeIds[n2]]

        before = node1.distProduct * node2.distProduct
        after1 = 1.0
        for partner in node1.partners:
            if partner != node2: # avoid multiplying by 0
                after1 *= getDistance(node2.location, partner.location)
            else: after1 *= getDistance(node2.location, node1.location) # same as before!
        after2 = 1.0
        for partner in node2.partners:
            if partner != node1: # avoid multiplying by 0
                after2 *= getDistance(node1.location, partner.location)
            else: after2 *= getDistance(node1.location, node2.location)
        after = after1 * after2

        # conditions for not switching locations:
        # if prod. of distances before < prod of distances after, then
        #   switch with probability P = before/after
        #print "Before: ", before, ", After: ", after, ", P(switch) = ", float(before) / after

        if before < after:
            if random.random() > before / after: # random float between 0 and 1 bigger than probability of switch -> don't switch
                return False # no switch

        # switch:
        # update partners' distProducts!
        for partner in node1.partners:
            if partner != node2: # avoid multiplying by 0
                partner.distProduct /= getDistance(node1.location, partner.location)
                partner.distProduct *= getDistance(node2.location, partner.location)
        for partner in node2.partners:
            if partner != node1: # avoid multiplying by 0
                partner.distProduct /= getDistance(node2.location, partner.location)
                partner.distProduct *= getDistance(node1.location, partner.location)
        node1.location, node2.location = node2.location, node1.location
        node1.distProduct = after1
        node2.distProduct = after2
        return True

    # save new locations to DB
    def save(self):
        sqlStr = "update ripple_nodes set location = %.12f where id = %d"
        conn = db_module.connect(DSN) # could get Django's connection here, but would need to make sure it wasn't doing anything else that might interfere/commit prematurely
        cursor = conn.cursor()
        try: # begin transaction
            for nodeId in self.shuffleNodes:
                cursor.execute(sqlStr % (self.shuffleNodes[nodeId].location, nodeId))
            conn.commit()
        except Exception, e:
            conn.rollback()

    # returns log(product of all connection distances in network)
    def getDistProduct(self):
        prod = 1.0
        mag = 0.0
        for nodeId in self.shuffleNodes:
            prod *= self.shuffleNodes[nodeId].distProduct
            if prod > 1e200 or prod < 1e-200:
                mag += math.log(prod, 10)
                prod = 1.0
        return mag

# stores node, location, partners, and current product of distances to partners
class ShuffleNode:
    def __init__(self, id, location):
        self.id = id
        self.location = location
