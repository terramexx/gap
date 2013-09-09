import os
from app.settings import settings
from common.test_base.test_base import TestBase
from contrib.domain_auth.decorators import domain_account_required, domain_bound
from contrib.domain_auth.model import Domain


class AbortException(BaseException):
    pass


class OkException(BaseException):
    pass


class TestDecorators(TestBase):

    USER_HOME_DOMAIN = 'test@github-gap.com'
    USER_OUT_DOMAIN = 'test@out-github.gap.com'
    DOMAIN_NAME = 'github-gap.com'

    _multiprocess_shared_ = False
    _multiprocess_can_split_ = False

    @classmethod
    def setUpClass(cls):
        TestBase.setUpClass()
        cls.testbed.init_user_stub()

    def setUp(self):
        Domain.create(TestDecorators.DOMAIN_NAME).put()

    @domain_bound
    @domain_account_required
    def _ensure_called_domain_validation_method(self, domain, *args, **kwargs):
        pass

    @domain_bound
    @domain_account_required(require_admin=True)
    def _ensure_called_domain_admin_validation_method(self, domain, *args, **kwargs):
        pass

    @domain_bound
    @domain_account_required
    def _not_call_this_method_domain(self, domain, *args, **kwargs):
        self.assertFalse("Unexpected method call")

    @domain_bound
    @domain_account_required(require_admin=True)
    def _not_call_this_method_domain_admin(self, domain, *args, **kwargs):
        self.assertFalse("Unexpected method call")

    @classmethod
    def _login_user(cls, email=None, is_admin=False):
        cls.testbed.setup_env(
            USER_EMAIL=email if email else TestDecorators.USER_HOME_DOMAIN,
            USER_ID='123',
            USER_IS_ADMIN='1' if is_admin else '0',
            overwrite=True)

    def abort(self, code, *args, **kwargs):
        raise AbortException()

    def test_domain_bound_existing_domain(self):
        self._ensure_called_domain_validation_method(TestDecorators.DOMAIN_NAME)

    def test_domain_bound_not_existing_domain(self):
        try:
            self._not_call_this_method_domain("incorrect-%s" % TestDecorators.DOMAIN_NAME)
        except AbortException:
            pass

    def test_domain_account_required(self):
        domain_account_required()

    def test_domain_account_required_domain_correct(self):
        """ domain_account_required - correct domain """
        TestDecorators._login_user()
        self._ensure_called_domain_validation_method(TestDecorators.DOMAIN_NAME)

    def test_domain_account_required_domain_incorrect(self):
        """ domain_account_required - incorrect domain """
        TestDecorators._login_user()
        try:
            self._not_call_this_method_domain("incorrect-%s" % TestDecorators.DOMAIN_NAME)
        except AbortException:
            pass

    def test_domain_account_required_appengine_admin_allowed(self):
        """ domain_account_required - correct domain """
        settings['allow_appengine_admins'] = True
        TestDecorators._login_user(email=TestDecorators.USER_OUT_DOMAIN, is_admin=True)
        try:
            self._ensure_called_domain_admin_validation_method(TestDecorators.DOMAIN_NAME)
        except OkException:
            pass

    def test_domain_account_required_appengine_admin_allowed_not_admin(self):
        """ domain_account_required - correct domain """
        settings['allow_appengine_admins'] = True
        TestDecorators._login_user(email=TestDecorators.USER_OUT_DOMAIN, is_admin=False)
        self._not_call_this_method_domain_admin(TestDecorators.DOMAIN_NAME)

    def test_domain_account_required_appengine_admin_not_allowed(self):
        """ domain_account_required - appengine admin but admins not required """
        settings['allow_appengine_admins'] = False
        TestDecorators._login_user(email=TestDecorators.USER_OUT_DOMAIN, is_admin=True)
        self._not_call_this_method_domain_admin(TestDecorators.DOMAIN_NAME)
