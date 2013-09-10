from gapi.exceptions import GoogleApiHttpException
from gapi.multipart import ResponseMock
from google.appengine.api.namespace_manager import namespace_manager
from google.appengine.ext.webapp.mock_webapp import MockResponse
from jinja2.exceptions import TemplateNotFound
from app.settings import settings
from common.test_base.test_base import TestBase
from contrib.domain_auth.decorators import domain_account_required, domain_bound
from contrib.domain_auth.model import Domain


class CalledException(BaseException):
    pass


class AbortException(BaseException):
    pass


class TestDecorators(TestBase):

    HOME_DOMAIN_NAME = 'github-gap.com'
    USER_FROM_HOME_DOMAIN = 'test@%s' % HOME_DOMAIN_NAME
    USER_FROM_EXTERNAL_DOMAIN = 'test@external-github.gap.com'
    USER_HOME_DOMAIN_ADMIN = 'admin@%s' % HOME_DOMAIN_NAME

    _multiprocess_shared_ = False
    _multiprocess_can_split_ = False

    response = MockResponse()

    @classmethod
    def _prepare_api_service(cls):
        from gapi.client import ApiService, ApiResource

        class Service(ApiService):

            _base_url = 'https://www.googleapis.com/admin/directory/v1'
            _default_scope = 'https://www.googleapis.com/auth/admin.directory.user.readonly'

            @property
            def _resources(self):
                return [Users]

        ApiService._services['directory'] = Service

        class Users(ApiResource):
            _name = 'users'
            _methods = ['list']
            _base_path = '/users'

            def _api_list(self, **kwargs):
                if self._service.email == TestDecorators.USER_HOME_DOMAIN_ADMIN:
                    return []
                raise GoogleApiHttpException(ResponseMock(500, '', None, None, None))

    @classmethod
    def setUpClass(cls):
        TestBase.setUpClass()
        cls.testbed.init_user_stub()
        cls._prepare_api_service()

    def setUp(self):
        Domain.create(TestDecorators.HOME_DOMAIN_NAME).put()
        namespace_manager.set_namespace(TestDecorators.HOME_DOMAIN_NAME)
        self.response.clear()

    @domain_bound
    def _domain_bound_method(self, domain, *args, **kwargs):
        pass

    @domain_bound
    @domain_account_required
    def _domain_account_method(self, domain, *args, **kwargs):
        raise CalledException()

    @domain_bound
    @domain_account_required(require_admin=True)
    def _domain_account_admin_method(self, domain, *args, **kwargs):
        raise CalledException()

    @classmethod
    def _login_user(cls, email=None, is_gae_admin=False):
        cls.testbed.setup_env(
            USER_EMAIL=email if email else TestDecorators.USER_FROM_HOME_DOMAIN,
            USER_ID='123',
            USER_IS_ADMIN='1' if is_gae_admin else '0',
            overwrite=True)

    def abort(self, code, *args, **kwargs):
        raise AbortException()

    def test_domain_bound_existing_domain(self):
        """ domain_bound - existing domain """
        self._domain_bound_method(TestDecorators.HOME_DOMAIN_NAME)

    def test_domain_bound_not_existing_domain(self):
        """ domain_bound - not existing domain """
        try:
            self._domain_bound_method("domain.not.ex")
        except AbortException:
            pass

    def test_domain_account_required_domain_correct(self):
        """ domain_account_required - user from correct domain """
        TestDecorators._login_user()

        def do_call():
            self._domain_account_method(TestDecorators.HOME_DOMAIN_NAME)
        self.assertRaises(CalledException, do_call)

    def test_domain_account_required_domain_incorrect(self):
        """ domain_account_required - incorrect domain """
        TestDecorators._login_user()
        try:
            self._domain_account_method("domain.incorrect.is")
        except AbortException:
            pass

    def test_domain_account_required_appengine_admin_allowed(self):
        """ domain_account_required - appengine admin allowed, admin user """
        settings['allow_appengine_admins'] = True
        TestDecorators._login_user(email=TestDecorators.USER_FROM_EXTERNAL_DOMAIN, is_gae_admin=True)

        try:
            self._domain_account_admin_method(TestDecorators.HOME_DOMAIN_NAME)
        except CalledException:
            pass

    def test_domain_account_required_appengine_admin_allowed_not_admin(self):
        """ domain_account_required - appengine admin allowed, not admin user """
        settings['allow_appengine_admins'] = True
        TestDecorators._login_user(email=TestDecorators.USER_FROM_EXTERNAL_DOMAIN, is_gae_admin=False)
        try:
            self._domain_account_admin_method(TestDecorators.HOME_DOMAIN_NAME)
        except TemplateNotFound, tnf:
            assert tnf.message == 'contrib/domain_auth/templates/domain_access_denied.html'
        # self.assertRegexpMatches(self.response, '<title>Access denied</title>')

    def test_domain_account_required_appengine_admin_not_allowed(self):
        """ domain_account_required - appengine admin not allowed, admin user """
        settings['allow_appengine_admins'] = False
        TestDecorators._login_user(email=TestDecorators.USER_FROM_HOME_DOMAIN, is_gae_admin=True)
        try:
            self._domain_account_admin_method(TestDecorators.HOME_DOMAIN_NAME)
        except TemplateNotFound, tnf:
            assert tnf.message == 'contrib/domain_auth/templates/domain_access_denied.html'
        # self.assertRegexpMatches(self.response, '<title>Access denied</title>')

    def test_domain_account_required_appengine_admin_not_allowed_domain_admin(self):
        """ domain_account_required - appengine admin not allowed, domain admin """
        settings['allow_appengine_admins'] = False
        TestDecorators._login_user(email=TestDecorators.USER_HOME_DOMAIN_ADMIN, is_gae_admin=False)

        def do_call():
            self._domain_account_admin_method(TestDecorators.HOME_DOMAIN_NAME)
        self.assertRaises(CalledException, do_call)
