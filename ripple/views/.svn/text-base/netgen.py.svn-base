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
Social network generator combining preferential 
attachment (which results in scale-free networks) and
uniform attachment, as described at
http://www.modelingtheweb.com/
"""

import random

"""
function generate
- nodes are numbered 0..n-1
- returns a list of pairs of nodes representing connections
- args: nodes = number of nodes desired
        avg_conn = target average # of connections per node
        pref_coeff = a number between 0 and 1,
            weight of preferential selection vs. uniform 
            (alpha in Pennock et al.)
"""
def generate( nodes, avg_conn, pref_coeff, seed=None ):
    conn = nodes * [0]
    conn[0] = conn[1] = 1
    edges = [(1,0)]
    avg = (float(avg_conn) / 4) + (1.6 * (1 - pref_coeff))
    if seed:
        random.seed(seed)
    
    for t in range( 2, nodes ):
        #print t, "\r",
        for i in range( t ):
            p = float( 1 - pref_coeff ) / (t + 1)
            if len( edges ) != 0:
                p = p + (float( pref_coeff ) * conn[i] / len( edges ))
            p = p * avg
            if random.random() < p:
                edges.append( (t, i) )
                conn[t] += 1
                conn[i] += 1
    printStats( conn )
    return edges

def printStats( conn ):
    for i in range( 0, max(conn) + 1 ):
        print "Nodes with", i, "connections:", len( filter( lambda x: x == i, conn ) ) 
    print "\nAverage connections:", float( sum(conn) ) / len(conn)
