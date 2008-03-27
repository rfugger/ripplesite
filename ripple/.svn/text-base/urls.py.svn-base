from django.conf.urls.defaults import *

urlpatterns = patterns(
    'ripplesite.ripple.views',
    (r'^$', 'home'),
    (r'^login/?$', 'login'), # handles both GET and POST
    (r'^logout/?$', 'logout'),
    (r'^register/?$', 'register'), # handles both GET and POST
    (r'^registrationSuccess/?$', 'registrationSuccess'),
    (r'^confirmEmail/(?P<code>\d+)/?$', 'confirmEmail'), # *** change to be /emails/id/confirm/
    (r'^profile/?$', 'profile'),
    (r'^emails/(?P<emailId>\d+)/(?P<action>delete|makePrimary|sendConfirmation)/?$', 'emailAction'),
    (r'^emails/add/?$', 'addEmail'),
    (r'^forgotPassword/?$', 'forgotPassword'),
    (r'^passwordReminderSent/?$', 'passwordReminderSent'),
    (r'^resetPassword/(?P<code>\d+)/?$', 'resetPassword'),
    (r'^resetPasswordSuccess/?$', 'resetPasswordSuccess'),
    (r'^about/?$', 'about'),
    (r'^faq/?$', 'faq'),
    (r'^contact/?$', 'contact'),
    (r'^summary/?$', 'summary'),
    (r'^essay/?$', 'essay'),
    (r'^donate/?$', 'donate'),
    
    (r'^paymentForm/?$', 'payment.paymentForm'),
    (r'^payUser/(?P<otherUserId>\d+)/?$', 'payment.paymentForm'),
    (r'^payments/(?P<pmtId>\d+)/confirm/?$', 'payment.confirmPayment'),
    (r'^pay/(?P<pmtId>\d+)/?$', 'payment.pay'),
    (r'^payments/?$', 'payment.paymentList'),
    (r'^payments/(?P<pmtId>\d+)/?$', 'payment.paymentDetail'),
    (r'^payments/(?P<pmtId>\d+)/edit/?$', 'payment.paymentForm'),
    (r'^payments/(?P<pmtId>\d+)/editRequest/?$', 'payment.paymentForm', {'is_request': True}),
    (r'^payments/(?P<pmtId>\d+)/cancel/?$', 'payment.cancelPayment'),
    (r'^requestPayment/?$', 'payment.paymentForm', {'is_request': True}),
    (r'^requestPayment/(?P<otherUserId>\d+)/?$', 'payment.paymentForm', {'is_request': True}),
    (r'^registerIOU/?$', 'payment.registerIOU'),
    (r'^registerIOU/(\d+)/?$', 'payment.registerIOU'),
    
    (r'^accounts/?$', 'connection.accountList'),
    (r'^accounts/(?P<acctId>\d+)/?$', 'connection.accountDetail'),
    (r'^accounts/(?P<acctId>\d+)/rate/(?P<action>accept|reject)/?$', 'connection.interestRateAction'),
    (r'^confirmClose/(?P<acctId>\d+)/?$', 'connection.confirmClose'), # *** change to be /accounts/id/confirmClose/
    (r'^accounts/(?P<acctId>\d+)/(?P<action>close)/?$', 'connection.accountAction'),
    (r'^offer/?$', 'connection.offer'),
    (r'^leaveNote/(?P<offerId>\d+)/?$', 'connection.rejectionNote'),
    (r'^offers/(?P<offerId>\d+)/(?P<action>accept|reject|withdraw)/?$', 'connection.offerAction'),
)
