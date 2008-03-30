from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns(
    '',
    (r'^', include('ripplesite.ripple.urls')),
    (r'^market/', include('ripplesite.market.urls')),
    
    # Uncomment this for admin:
    (r'^admin/', include('django.contrib.admin.urls')),
    
    #(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
      (r'^site_media/(?P<path>.*)$', 'django.views.static.serve',
       {'document_root':'/home/thartman/ripplesite/ripple/media'}),


)
