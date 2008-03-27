RippleSite version 0.2 README 
----------------------------- 

by Ryan Fugger
ryan@ripplepay.com 
http://ripple.sourceforge.net/

License 
------- 

The RippleSite software package, including source code, HTML templates, 
documentation, artwork, and all other included files, is covered by the 
GNU General Public License, a copy of which can be found in LICENSE.txt 
in the same directory as this README.  

-- 
RippleSite Standalone Ripple Web Service Software
Copyright (C) 2006-07

This program is free software; you can redistribute it and/or modify it 
under the terms of the GNU General Public License as published by the 
Free Software Foundation; either version 2 of the License, or (at your 
option) any later version.

This program is distributed in the hope that it will be useful, but 
WITHOUT ANY WARRANTY; without even the implied warranty of 
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General 
Public License for more details.

You should have received a copy of the GNU General Public License along 
with this program; if not, write to the Free Software Foundation, Inc., 
59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
--

Description 
----------- 

RippleSite is an open source version of the server software used to run 
RipplePay.com, a free web service for hosting Ripple payment networks on 
a single server. (For more information about the Ripple payment concept, 
see http://ripple.sourceforge.net/.) To get RippleSite running on your 
web server, it will take a bit of Python, Apache, and PostgreSQL 
know-how. If you don't have this, you probably shouldn't be operating a 
RippleSite server. 

Installation 
------------ 

RippleSite 0.3 works on the Django Python web application framework 
version 0.95, which can be downloaded from 
http://www.djangoproject.com/download/0.95.2/tarball/. More information 
about installing Django can be found at 
http://www.djangoproject.com/documentation/0.95/install/. In particular, 
RippleSite requires the following software: 

* Python 2.3 or higher (tested on 2.4) 
* Apache + mod_python (tested on Apache 2.0 -- may be configured for 
lighttpd + fast_cgi, not tested), although you can run the django
development server to try it out first
* PostgreSQL (tested on 8.0 and 8.1 -- may be configured to work on MySQL 
or sqlite3, not tested) 

The Django project website has a terrific tutorial that anyone 
installing RippleSite should go through. 

1. Start a new Django project called 'ripplesite' by running 'python 
django-admin.py startproject ripplesite', and copy the RippleSite files 
to the project directory. Make sure the parent directory of the the 
ripplesite project directory is in your PYTHONPATH so the ripplesite 
module can be loaded.

2. See the file settings_ripplesite.py for settings required for 
RippleSite. Make sure all of these fields are set in your settings.py. 
You will have to have created a database in PostgreSQL before you can
enter the database settings.

3. Run 'python manage.py syncdb' to initialize the database. (Optionally
run 'python manage.py sqlindexes ripple' to output the SQL statements for
creating database indexes -- copy or pipe these into psql to actually 
create your indexes.) 

4. Configure Apache. There are many ways to do this, but one way is to 
put something like the following in httpd.conf: 

-- 
<Location "/"> 
  SetHandler python-program 
  PythonHandler django.core.handlers.modpython 
  SetEnv DJANGO_SETTINGS_MODULE ripplesite.settings
  PythonPath "['/path/to/parent'] + sys.path" 
  PythonDebug Off 
</Location> 
  
<Location "/media/">
  SetHandler None 
</Location> 
-- 

* /path/to/parent is the path to the parent directory of the
ripplesite project directory

You must also create a symbolic link to the admin media files from 
within your Apache document root. There is more information on how to 
configure Apache for Django + mod_python at:

http://www.djangoproject.com/documentation/modpython/

5. Browse to /admin/ on your site, log into the Django admin app (which 
should hopefully be working by now), click on Currency units and create 
the currency units you'd like your users to be able to choose on your 
site. If you'd like to use US dollars, for example, create a currency 
unit with short name 'USD', long name 'US Dollar', symbol '$', and value 
1.0. You can always create more later, but you'll need at least one to 
start with. 

If you have multiple units that you want Ripple to be able to 
automatically convert between, set their relative values in the value 
fields. For example, if you had US dollars set to a value of 1.0, 
Canadian dollars would be set to around 0.90 because one dollar Canadian 
is currently worth about 90 cents US. (I've included the script 
getrates.py in the scripts directory which will fetch current exchange 
rates from Yahoo and output SQL statements for updating the database -- 
that should be a decent starting point for piecing together an 
auto-update system.) 

6. Browse to the root on your site and create a new user. Send out some 
invitations to people you know... 

7. You can customize your home page by modifying the file 
ripple/templates/home.html. 

8. You may want to set up a forum where your users can find items they 
can buy with Ripple. Suggestions are a web forum, a Yahoo group, a 
Google group, or Craigslist. In the case of the latter two public 
forums, if you direct your users to include a special prefix such as 
*VanRipple* (if your service was called VanRipple) with every post, they 
will be able to search specifically for Ripple items. 

9. If you expect a lot of users, remember you can get a lot better 
performance by creating the indexes generated by python manage.py 
sqlindexes and tuning your PostgreSQL installation. See 
http://www.revsys.com/writings/postgresql-performance.html. 

Contact Info 
------------ 

If you need help getting your Ripple site set up, have a feature request 
to make, or better yet, have some improvements to the code that you wish 
to contribute to the project (I should be so lucky), please post to the 
Ripple project forums at https://sourceforge.net/forum/?group_id=120019. 
I am also currently (Feb. 2007) working on a P2P version of Ripple to 
eventually be integrated with RippleSite, if anyone would like to help. 

Ideas for Improvements 
---------------------- 

If you feel like improving the code, here are some ideas for things to 
work on: 

* improve the site design and layout (I'm not a web designer)
* write an installation script 
* integrate admin-driven news items into the front page 
* paginate payment history in both account and payment views 
* allow user to request payment from other users 
* allow multiple accounts between two users (may simply be a case of 
removing the check for this when creating new account and testing 
that it works with payments) 
* allow users to view current conversion rates 
* allow users to print up certificates and/or generate codes that may 
be given to other users and redeemed on the system, for face-to-face 
transactions 
* translations into other languages 
* make email notifications optional and/or encrypt them with user's 
PGP key 
* security question for resetting password 
* longer confirmation/forgot password codes 
* credit/reputation checks - request permission from user to find out 
maximum amount they could pay you 
* contact form on contact page 
* improve test-cookie login handling (these test sessions build up and 
have to be cleared periodically) 
* change account units 
* transfer between accounts 
* invite-only registrations 
* resend invitation or receipt 
* split off user/login info from Node model and use builtin Django User 
instead 

