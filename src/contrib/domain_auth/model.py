from google.appengine.api import namespace_manager
from google.appengine.ext import ndb


class Domain(ndb.Model):
    """
        Domain entity

        key = domain name
    """
    createdDate = ndb.DateTimeProperty(indexed=False, auto_now_add=True)
    primary = ndb.BooleanProperty(default=True)
    version = ndb.IntegerProperty(default=1)

    def __init__(self, *args, **kwargs):
        super(Domain, self).__init__(*args, **kwargs)

    def _get_name(self):
        return self.key.id()
    name = property(_get_name)

    def _get_url_context(self):
        return '/v/%s' % self.name
    url_context = property(_get_url_context)

    @staticmethod
    def create(domain_name):
        return Domain(id=domain_name)

    @staticmethod
    def get_by_name(domain_name):
        return ndb.Key(Domain, domain_name).get()

    @staticmethod
    def set(domain_name):
        domain = Domain.get_by_name(domain_name)
        if domain:
            namespace_manager.set_namespace(domain.name)
        return domain
