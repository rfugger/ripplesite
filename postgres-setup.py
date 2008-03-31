#!/usr/bin/python
import stat, sys, os, string, commands, re

def createPgUser():


    pgO = commands.getoutput(""" sudo su postgres -c 'psql -c "\du"' """)
    whoiam = commands.getoutput("whoami")
    if not ( re.search(whoiam,pgO) ):
        print "creating user" + whoiam + "\n"
        c = """ sudo su postgres -c "createuser --no-adduser --no-createrole --createdb `whoami`"   """
        print (commands.getoutput(c))
    else:
        print "user " + whoiam + " exists\n"

def createPgDb():
    pgO = commands.getoutput(""" sudo su postgres -c 'psql -c "\li"' """)
    db = "ripplesite"
    if not ( re.search(db,pgO) ):
        print "creating db ripplesite\n"
        c = """ createdb ripplesite   """
        print (commands.getoutput(c))
        print "run python manage.py syncdb next.\n"
    else:
        print "db ripplesite exists. if you want to drop it, do dropdb ripplesite before running this script"
        
#Getting search pattern from user and assigning it to a list

try:
    createPgUser()
    createPgDb()

except:
        print "There was a problem - check the message above"



