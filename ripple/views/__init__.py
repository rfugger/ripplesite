"""
Main views file
"""

from django.core import template_loader
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.db.models import Q
from django.core.mail import send_mail
from django.utils.html import escape
from django.utils import safestring

from ripplesite.ripple.models import *
import routing
from django.conf import settings

import datetime, re, random, sha
from smtplib import SMTPException
from socket import gaierror

def creditpath(request):
    return render_to_response('creditpath.html')

def home_interpersonal(request):
    userNode = checkLogin(request)
    d = {}
    """
    if not userNode: # not logged in - show home page
        request.session.set_test_cookie()        
        # some usage data for front page
        d['num_users'] = Node.objects.count()
        d['num_accounts'] = SharedAccountData.objects.count()
        d['num_payments'] = Payment.objects.count()
        
        d['HOME_INTRO_TEXT'] = settings.HOME_INTRO_TEXT
    """

    return render_to_response('home_interpersonal.html', d, context_instance=RequestContext(request))

def inbox(request):
    userNode = checkLogin(request)
    d = {}
    return render_to_response('inbox.html', d, context_instance=RequestContext(request))

def summary(request):
    """The users home page"""
    d = {}

    # get user's Node
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    d['userNode'] = userNode

    # get any error messages from session
    d['infos'] = getSessionInfos(request)

    # outstanding offers of credit received/made
    d['receivedOffers'] = Offer.objects.filter(recipient_email__in=getEmails(userNode)).order_by('-id')
    #d['sentOffers'] = userNode.sent_offer_set.order_by('-id')

    d['rateProposals'] = getRateProposalAccts(userNode)
    
    # number of connections
    d['numAccounts'] = userNode.account_set.filter(shared_data__active=True).count()

    # account balances etc. summary
    acctUnits = getAccountsSummary(userNode)
    d['totalBalance'] = 0.0
    d['totalOutCredit'] = 0.0
    d['totalInCredit'] = 0.0
    for unit in acctUnits:
        unit.display = True
        unit.displayBalance = unit.balance
        unit.displayOutCredit = unit.availOutCredit
        unit.displayInCredit = unit.availInCredit
        # if displaying in default units, convert and sum
        if userNode.display_units_id:
            if unit.value:
                unit.displayBalance *= unit.value / userNode.display_units.value
                d['totalBalance'] += unit.displayBalance
                unit.displayOutCredit *= unit.value / userNode.display_units.value
                d['totalOutCredit'] += unit.displayOutCredit
                unit.displayInCredit *= unit.value / userNode.display_units.value
                d['totalInCredit'] += unit.displayInCredit
            else: # can't convert to default units, so can't display
                unit.display = False

    convertibleUnits = CurrencyUnit.objects.filter(value__gt=0.0).order_by('long_name')
    hasConvertibleAcct = False
    for unit in acctUnits:
        if unit in convertibleUnits:
            hasConvertibleAcct = True
            break
    if not hasConvertibleAcct:
        convertibleUnits = None
    #else: # move default units to the top of the list
    #  for unit in convertibleUnits:
    #    if unit.id == userNode.display_units_id:
    #      convertibleUnits[:0] = [convertibleUnits.pop(convertibleUnits.index(unit))]
    d['accountUnits'] = acctUnits
    d['convertibleUnits'] = convertibleUnits

    # get recent payments list
    from payment import prepPaymentsForDisplay # do it here to avoid circular import problem
    d['payments'] = Payment.objects.filter(Q(payer=userNode) | Q(recipient=userNode),
                                           status='OK'
                                           ).order_by('-date')[:4]
    prepPaymentsForDisplay(d['payments'], userNode)

    d['paymentRequests'] = Payment.objects.filter(payer=userNode, status='RQ'
                                                  ).order_by('-date')[:4]

    return render_to_response('summary.html', d, context_instance=RequestContext(request))

# retrieves user's node if logged in - otherwise returns None
def checkLogin(request):
    try: # reload node from id every time to be safe, since it may have been changed by last request
        nodeId = request.session['userNodeId']
        userNode = Node.objects.get(pk=nodeId)
    except KeyError, NodeDoesNotExist:
        return None
    return userNode

# get 'infos' key from session - used to pass informational messages for the user between pages
def getSessionInfos(request):
    if 'infos' in request.session:
        infos = request.session['infos']
        del request.session['infos']
    else:
        infos = []
    return infos

def getAccountsSummary(node):
    """ takes a node and returns a list of currencies, each with the following variables hacked in:
      - accts (node's accounts denominated in that currency)
      - balance (cumulative balance of accounts in that currency)
      - lowerLimit (as a positive number - actual balance limit is the negative of this)
      - upperLimit
      - availOutCredit (= balance + lowerLimit)
      - availInCredit (= upperLimit - balance)
    """
    units = []
    for acct in node.account_set.filter(shared_data__active=True).order_by('name'):
        acct.balance = acct.getBalance() # only compute present interest once
        unit = acct.shared_data.currency
        if unit not in units:
            unit.accts = []
            unit.balance = 0.0
            unit.lowerLimit = 0.0
            unit.availOutCredit = 0.0
            unit.upperLimit = 0.0
            unit.availInCredit = 0.0
            units.append(unit)
        unit = units[units.index(unit)] # load existing one to keep extra variables
        unit.accts.append(acct)
        unit.balance += acct.balance
        unit.lowerLimit += acct.iou_limit
        unit.availOutCredit += max(acct.balance + acct.iou_limit, 0.0)
        partner_acct = acct.get_partner_acct()
        unit.upperLimit += partner_acct.iou_limit
        unit.availInCredit += max(partner_acct.iou_limit - acct.balance, 0.0)

    units.sort(lambda a, b: cmp(a.long_name, b.long_name))
    return units

def login(request):
    """POST: login user, GET: display login form"""
    userNode = checkLogin(request)
    if userNode:
        return HttpResponseRedirect('/')
    
    d = {}
    errors = []
    if request.method == 'POST':
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()
        else: # cookie error requires a separate error page so user can enable cookies and reload login page to set test cookie again.
            d = {'message':'Please enable cookies and try your login again.', 'link':'/login/'}
            return render_to_response('error.html', d, context_instance=RequestContext(request))
        redirect = request.POST['redirect']
        username = request.POST['username']
        d['username'] = username
        password = request.POST['password']
        email = None
        
        if Node.objects.filter(username__iexact=username).count() > 0: # user entered username
            userNode = Node.objects.get(username__iexact=username)
            email = EmailAddr.objects.get(node=userNode, primary=True)
        
        elif EmailAddr.objects.filter(email__iexact=username).count() > 0: # user entered email address
            email = EmailAddr.objects.get(email__iexact=username)
            userNode = email.node
        
        # check password
        if email and userNode.checkPwd(password):
            if email.confirmed: # login
                    request.session['userNodeId'] = email.node_id # store only the id and reload every request in case of change
                    return HttpResponseRedirect(redirect)
            else:
                errors.append("You have not yet confirmed email address '%s' by clicking the link in your confirmation email." % escape(email.email))
                if sendConfirmationEmail(email.email, email.code, request):
                    errors.append('Your confirmation email has been resent.  If you do not receive it, <a href="/contact/">please contact us.</a>')
                else:
                    errors.append('Your confirmation email could not be resent. <a href="/contact/">Please contact us</a> if you cannot find your original confirmation email.')
        else:
            errors.append('Invalid login details. Please try again or <a href="/register/">click here to sign up as a new user</a>.')

    errors  = [safestring.mark_safe(item) for item in errors]

    # display login form
    d['infos'] = errors
    if request.GET:
        d['redirect'] = request.GET['redirect']
    request.session.set_test_cookie()
    return render_to_response('login.html', d, context_instance=RequestContext(request))

def logout(request):
    if 'userNodeId' in request.session:
        del request.session['userNodeId']
    return HttpResponseRedirect('/')

def register(request):
    """POST: register new user, GET: display registration form"""
    errors = []
    if request.method == 'POST':
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()
        else: # cookie error requires a separate error page so user can enable cookies and reload login page to set test cookie again.
            d = {'message':'Please enable cookies and try your registration again.', 'link':'/register/'}
            return render_to_response('error.html', d, context_instance=RequestContext(request))

        username = request.POST['username']
        if Node.objects.filter(username__iexact=username).count() > 0:
            errors.append("Username '%s' is taken." % username)

        name = request.POST['name']
        if name == '': name = username # default to username if name left blank

        email = request.POST['email']
        if EmailAddr.objects.filter(email__iexact=email).count() > 0:
            errors.append("Someone has already registered email '%s'." % escape(email))

        password = request.POST['password']
        confirmPassword = request.POST['confirmPassword']
        if password != confirmPassword:
            errors.append('The two passwords entered do not match.')
        if len(password) < 4:
            errors.append('Your password must be at least four characters long.')

        displayUnitsStr = request.POST['displayUnits']
        if displayUnitsStr == 'None':
            displayUnits = None
        else: # load units
            displayUnits = CurrencyUnit.objects.get(short_name=displayUnitsStr)

        if username == '' or email == '' or password == '':
            errors.append('You must fill in every field with a star beside it.')
            
        if not errors:
            # send email confirmation first
            code = makeConfirmationCode()
            if sendConfirmationEmail(email, code, request):
                hashedPwd = hash(password + code)
                newUser = Node(username=username, name=name, salt=code[:10], pwd=hashedPwd, location=routing.getNewLocation(), display_units=displayUnits, do_conversions=True)
                newUser.save()
                newEmail = EmailAddr(node=newUser, email=email, code=code, confirmed=False, primary=True)
                newEmail.save()
                # redirect to informational page
                return HttpResponseRedirect('/registrationSuccess/')
            else:
                errors.append('User not registered. A confirmation email could not be sent to %s. \
                        Please verfiy email address and/or try again later.' % escape(email))
        
        # add general error message
        generalError = 'There were errors with your registration.  Please correct them and try again.'
        errors = [generalError] + errors
    
    # display registration form
    request.session.set_test_cookie()
    d = {}
    d['infos'] = errors
    d['units'] = CurrencyUnit.objects.filter(value__gt=0.0).order_by('long_name') # must be convertible to be default units
    if request.method == 'POST':
        d['username'] = request.POST['username']
        d['name'] = request.POST['name']
        d['email'] = request.POST['email']
        d['displayUnits'] = request.POST['displayUnits']

    return render_to_response('registration.html', d, context_instance=RequestContext(request))

def makeConfirmationCode():
    while True:
        code = str(random.randint(1000000000, 9999999999))
        if EmailAddr.objects.filter(code=code).count() == 0:
            break
    return code

def hash(s):
    return sha.new(s).hexdigest()

# returns True if email sent, False otherwise
def sendConfirmationEmail(email, code, request):
    t = template_loader.get_template('emailConfirmation.txt')
    c = RequestContext(request, {'email':email, 'code':code})
    return sendEmail('Please confirm email address', t.render(c), email)

def sendEmail(subject, msg, recipient, sender=None, attempts=3, includeServiceName=True):
    if sender == None:
        sender = '"%s" <%s>' % settings.ADMINS[0]
    if includeServiceName:
        subject = '%s - %s' % (settings.SERVICE_NAME, subject)
    if settings.EMAIL_HOST == 'TEST_DEBUG':
        print "EMAIL_HOST not set.  Cannot send the following email:"
        print "To: %s" % recipient
        print "From: %s" % sender
        print "Subject: %s" % subject
        print "-----------"
        print msg
        return True  # pretend
    while attempts > 0:
        try:
            return send_mail(subject, msg, sender, (recipient,))
        except (SMTPException, gaierror):
            attempts -= 1
    return False

def registrationSuccess(request):
    return render_to_response('registrationSuccess.html', {}, context_instance=RequestContext(request))

def confirmEmail(request, code):
    userNode = checkLogin(request)
    if EmailAddr.objects.filter(code=code).count() > 0:
        email = EmailAddr.objects.get(code=code)
        if email.confirmed:
            d = {'message':'That email address has already been confirmed.', 'link':'/login/'}
            return render_to_response('error.html', d, context_instance=RequestContext(request))
    else:
        d = {'message':'Invalid confirmation code.', 'link':'/'}
        return render_to_response('error.html', d, context_instance=RequestContext(request))
    
    # set email to 'confirmed'/primary, and others for same node to secondary
    email.confirmed = True
    email.save()
    
    if userNode:
        if email.node == userNode:
            request.session['infos'] = ["Email address %s confirmed." % escape(email.email)]
            if EmailAddr.objects.filter(node=userNode).count() == 1:
                return HttpResponseRedirect('/summary/') # first time, send to summary
            else: 
                return HttpResponseRedirect('/profile/')
        else: # logged in as different user
            # logout
            if 'userNodeId' in request.session:
                del request.session['userNodeId']
    
    request.session.set_test_cookie() # necessary because this is a login page
    d = {'username':email.email}
    return render_to_response('confirmEmail.html', d, context_instance=RequestContext(request))

def profile(request):
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    d = {}
    
    # get any error messages from session
    d['infos'] = getSessionInfos(request)

    if request.method == 'POST':
        name = request.POST['name']
        if name != '' and name != userNode.name:
            userNode.name = name
            d['infos'].append("Name changed to %s." % name)
        
        password = request.POST['password']
        confirmPassword = request.POST['confirmPassword']
        if password != confirmPassword:
            d['infos'].append('The two new passwords entered do not match.  Password not changed.')
        elif len(password) < 4:
            d['infos'].append('Passwords must be at least four characters long.  Password not changed.')
        elif password != '':
            userNode.pwd = hash(password + userNode.salt)
            d['infos'].append('Password changed.')
        
        displayUnits = request.POST['displayUnits']
        if displayUnits == 'None' and userNode.display_units_id:
            userNode.display_units_id = None
            d['infos'].append('Account display units set to None.')
        elif CurrencyUnit.objects.filter(short_name=displayUnits).count() > 0:
            curr = CurrencyUnit.objects.get(short_name=displayUnits)
            if userNode.display_units_id != curr.id:
                userNode.display_units_id = curr.id
                d['infos'].append('Default account display units changed to %s.' % escape(displayUnits))
        
        if request.POST['convert'] == 'no':
            doConversions = False
        else:
            doConversions = True
        if doConversions != userNode.do_conversions:
            userNode.do_conversions = doConversions
            if doConversions:
                d['infos'].append('Conversions between account units enabled.')
            else:
                d['infos'].append('Conversions between account units disabled.')
        
        userNode.save()
    
    d['userNode'] = userNode
    d['units'] = CurrencyUnit.objects.filter(value__gt=0.0).order_by('long_name') # must be convertible to be default units
    if userNode.display_units_id:
        d['displayUnits'] = userNode.display_units
    else:
        d['displayUnits'] = None
    d['emails'] = userNode.emailaddr_set.order_by('-primary')
    return render_to_response('profile.html', d, context_instance=RequestContext(request))

# takes string and returns a list of email addresses in the string with no repeats
def parseEmails(text):
    patternLenient = r"\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*" # lenient email-matching pattern
    matches = re.finditer(patternLenient, text)
    emails = []
    for match in matches:
        nextEmail = text[match.start():match.end()]
        if nextEmail not in emails:
            emails.append(nextEmail)
    return list(emails)

def isEmail(email):
    emails = parseEmails(email)
    if len(emails) == 1 and emails[0] == email:
        return True
    else: return False

# context processor for automatically inserting userNode into RequestContext
# activated in settings.py under TEMPLATE_CONTEXT_PROCESSORS
def userNode_proc(request):
    return {'userNode':checkLogin(request)}
    
# context processor for automatically inserting site info into RequestContext
# activated in settings.py under TEMPLATE_CONTEXT_PROCESSORS
def siteInfo_proc(request):
    d = {}
    d['SITE_NAME'] = settings.SITE_NAME
    d['SERVICE_NAME'] = settings.SERVICE_NAME
    d['ADMIN_NAME'] = settings.ADMINS[0][0]
    d['ADMIN_EMAIL'] = settings.ADMINS[0][1]
    return d

# used to show IE 6 and below a GIF instead of the nice PNG logo
def userAgent_proc(request):
    agent = request.META['HTTP_USER_AGENT']
    ie = (agent.count('MSIE') > 0 and agent.count('MSIE 7') == 0)
    return {'iexplorer': ie}

# generic class for holding any types of data
class Struct:
    pass

def construction(request):
    return render_to_response('construction.html', {}, context_instance=RequestContext(request))

def contact(request):
    return render_to_response('contact.html', {}, context_instance=RequestContext(request))

def about(request):
    return render_to_response('about.html', {}, context_instance=RequestContext(request))

def faq(request):
    return render_to_response('faq.html', {}, context_instance=RequestContext(request))

def getEmails(node, confirmed=True):
    if confirmed:
        emails = EmailAddr.objects.filter(node=node, confirmed=True)
    else:
        emails = EmailAddr.objects.filter(node=node)
    return [e.email for e in emails]

def emailAction(request, emailId, action):
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=/profile/')
    
    if EmailAddr.objects.filter(pk=emailId).count() == 0:
        return HttpResponseRedirect('/profile/')
    
    email = EmailAddr.objects.get(pk=emailId)
    if email.node_id != userNode.id:
        return HttpResponseRedirect('/profile/')
    
    if action == 'delete':
        if not email.primary:
            email.delete()
            request.session['infos'] = ["Email address %s deleted from profile." % escape(email.email)]
        else:
            request.session['infos'] = ["Cannot delete primary email address."]
    
    elif action == 'makePrimary':
        if email.confirmed:
            oldPrimary = EmailAddr.objects.get(node=userNode, primary=True)
            oldPrimary.primary = False
            oldPrimary.save()
            email.primary = True
            email.save()
            request.session['infos'] = ["%s is now your primary email." % escape(email.email)]
        else:
            request.session['infos'] = ["Cannot make %s your primary address until it is confirmed." % escape(email.email)]
    
    elif action == 'sendConfirmation':
        if not email.confirmed:
            if sendConfirmationEmail(email.email, email.code, request):
                request.session['infos'] = ["Confirmation email resent to %s." % escape(email.email)]
            else:
                request.session['infos'] = ['Confirmation email could not be resent to %s.  Please try again in a few minutes or <a href="/contact/">contact us.</a>' % escape(email.email)]
        else:
            request.session['infos'] = ["%s already confirmed." % escape(email.email)]
            
    return HttpResponseRedirect('/profile/')

def addEmail(request):
    userNode = checkLogin(request)
    if not userNode: return HttpResponseRedirect('/login/?redirect=%s' % request.path)
    
    if not request.POST:
        return HttpResponseRedirect('/profile/')
    
    email = request.POST['addEmail']
    if not isEmail(email):
        request.session['infos'] = ["'%s' is not a valid email address.  Please try again." % escape(email)]
        return HttpResponseRedirect('/profile/')
    
    if EmailAddr.objects.filter(email=email).count() > 0:
        request.session['infos'] = ["%s is already registered." % escape(email)]
        return HttpResponseRedirect('/profile/')
    
    code = makeConfirmationCode()
    if not sendConfirmationEmail(email, code, request):
        request.session['infos'] = ['Confirmation email could not be resent to %s.  Please try again in a few minutes or <a href="/contact/">contact us.</a>' % escape(email.email)]
        return HttpResponseRedirect('/profile/')
    
    newEmail = EmailAddr(node=userNode, email=email, code=code, confirmed=False, primary=False)
    newEmail.save()
    request.session['infos'] = ["A confirmation email has been sent to %s." % escape(email)]
        
    return HttpResponseRedirect('/profile/')

def essay(request):
    return render_to_response('essay.html', {}, context_instance=RequestContext(request))

def forgotPassword(request):
    errors = []
    if request.method == 'POST':
        email = request.POST['email']
        if not isEmail(email):
            errors.append("%s does not appear to be a valid email address.  Please try again." % escape(email))
        
        if not errors:
            if EmailAddr.objects.filter(email=email).count() > 0:
                emailAddr = EmailAddr.objects.get(email=email)
                code = makeReminderCode()
                t = template_loader.get_template('emailForgotPassword.txt')
                c = RequestContext(request, {'email':email, 'code':code})
                if sendEmail('How to reset your password', t.render(c), email):
                    node = emailAddr.node
                    existingReminders = node.reminder_set.all()
                    for reminder in existingReminders:
                        reminder.delete() # only one oustanding reminder per node allowed
                    newReminder = Reminder(node=emailAddr.node, code=code)
                    newReminder.save()
                else:
                    errors.append("Could not send email to %s.  Please verify the email address and try again." % escape(email))
            else: # email address not in system
                pass # pretend like we're sending a reminder anyways, so no one knows whether an email is registered or not
        
        if not errors:
            return HttpResponseRedirect('/passwordReminderSent/')
    
    d = {}
    d['infos'] = errors
    return render_to_response('forgotPassword.html', d, context_instance=RequestContext(request))

def makeReminderCode():
    while True:
        code = str(random.randint(1000000000, 9999999999))
        if Reminder.objects.filter(code=code).count() == 0:
            break
    return code

def passwordReminderSent(request):
    return render_to_response('passwordReminderSent.html', {}, context_instance=RequestContext(request))

def resetPassword(request, code):
    if Reminder.objects.filter(code=code).count():
        reminder = Reminder.objects.get(code=code)
    else:
        return HttpResponseRedirect('/')
    
    errors = []
    if request.method == 'POST': # change password
    
        # *** add security question check here
        
        pwd = request.POST['password']
        confirm = request.POST['confirm']
        if pwd != confirm:
            errors.append("The two new passwords do not match.  Please try again.")
        elif len(pwd) < 4:
            errors.append("Passwords must have at least four characters.  Please try again.")
        if not errors:
            node = reminder.node
            node.pwd = hash(pwd + node.salt)
            node.save()
            reminder.delete()
            return HttpResponseRedirect('/resetPasswordSuccess/')
    
    # display reset password form
    d = {}
    d['infos'] = errors
    d['code'] = code
    return render_to_response('resetPassword.html', d, context_instance=RequestContext(request))
    
def resetPasswordSuccess(request):
    return render_to_response('resetPasswordSuccess.html', {}, context_instance=RequestContext(request))

def donate(request):
    return render_to_response('donate.html', {}, context_instance=RequestContext(request))

def getRateProposalAccts(node):
    return Account.objects.filter(owner=node, shared_data__node_to_confirm=node)

def rippledeals(request):
    #latest_poll_list = Poll.objects.all().order_by('pub_date')[:3]
    testvar="testvar"
    return render_to_response('rippledeals/index.html',{'testvar':testvar})
