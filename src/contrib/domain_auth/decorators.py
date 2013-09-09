from functools import wraps
import logging

from google.appengine.api import users

from app.template import get_template
from contrib.domain_auth.model import Domain
from contrib.domain_auth import utils


def domain_bound(fn):
    """
    Decorator which transforms domain name to its model value and passes it as function argument
    """
    def args_wrap(self, domain_name, *args, **kwargs):
        domain = Domain.set(domain_name)
        if not domain:
            self.abort(404, 'Domain %r not found' % domain_name)
        return fn(self, domain, *args, **kwargs)

    return args_wrap


def domain_account_required(fn=None, require_admin=False):
    """
    Decorator which ensures the logged in user has admin rights or has account from the requested domain

    This passes user from other domain only if a special flag allows that and the user is appengine application's admin
    """
    def _require_domain_account(fn):
        @wraps(fn)
        def args_wrap(self, domain, *args, **kwargs):

            auth = False
            if require_admin:
                logging.info('DOMAIN=%s, ADMIN USER' % domain.name)
                auth = utils.is_current_user_admin(domain)
            else:
                user = users.get_current_user()
                if user:
                    user_email = user.email()
                    user_name, user_domain = user_email.split('@')
                    logging.info('DOMAIN=%s, USER=%s' % (domain.name, user_email))
                    auth = domain.name == user_domain

            if auth:
                return fn(self, domain, *args, **kwargs)
            else:
                def force_login(self, domain):
                    self.response.out.write(
                        get_template('contrib/domain_auth/templates/domain_access_denied.html').render({
                            'domain_name': domain.name,
                            'login_url': users.create_login_url(domain.url_context),
                            'logout_url': users.create_logout_url(domain.url_context)
                        })
                    )

                return force_login(self, domain)
        return args_wrap

    if fn and callable(fn):
        return _require_domain_account(fn)
    else:
        return _require_domain_account
