from google.appengine.api import users, memcache

from app.settings import settings
from gapi import Api
from gapi.exceptions import GoogleApiHttpException


def _is_current_user_domain_admin(domain):
    """
    Checks if the current user is domain admin
    """
    current_user = users.get_current_user()
    if current_user is None:
        return False

    memcache_key = 'is_domain_admin_%s' % current_user.email()
    is_domain_admin = memcache.get(memcache_key)
    if is_domain_admin is not None:
        return is_domain_admin

    is_domain_admin = False
    try:
        api = Api(['directory'], settings['oauth_client_email'], settings['oauth_private_key'], current_user.email())
        api.directory.users.list(domain=domain.name, maxResults=1)
        is_domain_admin = True
    except (GoogleApiHttpException, IOError):
        pass

    memcache.add(memcache_key, is_domain_admin, 600)
    return is_domain_admin


def is_current_user_admin(domain):
    """
    Checks for admin rights of the logged in user

    True result for
    - the domain admin
    - the appengine admins if the 'allow_appengine_admins' flag is on

    False in all other variants
    """
    allow_appengine_admins = settings['allow_appengine_admins']
    is_appengine_admin = users.is_current_user_admin()
    return (allow_appengine_admins and is_appengine_admin) or _is_current_user_domain_admin(domain)
