from django.conf.urls.defaults import *

urlpatterns = patterns(
    'ripplesite.market.views',
    (r'^$', 'main'),
    (r'searchads','searchads'),
    (r'showads','showads'),
    (r'^new', 'new_ad'),
    (r'^(\d+)/$', 'view_ad'),
    (r'^sendmoney', 'sendmoney'),
)
