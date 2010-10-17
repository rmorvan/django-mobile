import threading
from django.conf import settings as django_settings
from django.template import TemplateDoesNotExist
from django.template.loaders import app_directories, filesystem
from django.test import TestCase
from mock import Mock, patch
from django_mobile import get_flavour, set_flavour
from django_mobile.conf import settings
from django_mobile.middleware import MobileDetectionMiddleware, \
    SetFlavourMiddleware


def _reset():
    '''
    Reset the thread local.
    '''
    import django_mobile
    del django_mobile._local
    django_mobile._local = threading.local()


class BaseTestCase(TestCase):
    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()


class BasicTests(BaseTestCase):
    def test_set_flavour(self):
        set_flavour('full')
        self.assertEqual(get_flavour(), 'full')
        set_flavour('mobile')
        self.assertEqual(get_flavour(), 'mobile')

        self.assertRaises(ValueError, set_flavour, 'spam')


class TemplateLoaderTests(BaseTestCase):
    def setUp(self):
        super(TemplateLoaderTests, self).setUp()
        self.original_TEMPLATE_LOADERS = settings.TEMPLATE_LOADERS
        self.original_FLAVOURS_TEMPLATE_LOADERS = settings.FLAVOURS_TEMPLATE_LOADERS
        django_settings.TEMPLATE_LOADERS = (
            'django_mobile.loader.Loader',
        )
        django_settings.FLAVOURS_TEMPLATE_LOADERS = (
            'django.template.loaders.filesystem.load_template_source',
            'django.template.loaders.app_directories.load_template_source',
        )

    def tearDown(self):
        super(TemplateLoaderTests, self).tearDown()
        django_settings.TEMPLATE_LOADERS = self.original_TEMPLATE_LOADERS
        django_settings.FLAVOURS_TEMPLATE_LOADERS = self.original_FLAVOURS_TEMPLATE_LOADERS

    @patch.object(app_directories.Loader, 'load_template_source')
    @patch.object(filesystem.Loader, 'load_template_source')
    def test_loader_on_filesystem(self, filesystem_loader, app_directories_loader):
        filesystem_loader.side_effect = TemplateDoesNotExist()
        app_directories_loader.side_effect = TemplateDoesNotExist()

        from django_mobile.loader import Loader
        loader = Loader()

        set_flavour('mobile')
        try:
            loader.load_template_source('base.html', template_dirs=None)
        except TemplateDoesNotExist:
            pass
        self.assertEqual(filesystem_loader.call_args[0][0], 'mobile/base.html')
        self.assertEqual(app_directories_loader.call_args[0][0], 'mobile/base.html')

        set_flavour('full')
        try:
            loader.load_template_source('base.html', template_dirs=None)
        except TemplateDoesNotExist:
            pass
        self.assertEqual(filesystem_loader.call_args[0][0], 'full/base.html')
        self.assertEqual(app_directories_loader.call_args[0][0], 'full/base.html')


class MobileDetectionMiddlewareTests(BaseTestCase):
    @patch('django_mobile.middleware.set_flavour')
    def test_mobile_browser_agent(self, set_flavour):
        request = Mock()
        request.META = {
            'HTTP_USER_AGENT': 'My Mobile Browser',
        }
        middleware = MobileDetectionMiddleware()
        middleware.process_request(request)
        self.assertEqual(set_flavour.call_args, (('mobile',), {}))

    @patch('django_mobile.middleware.set_flavour')
    def test_desktop_browser_agent(self, set_flavour):
        request = Mock()
        request.META = {
            'HTTP_USER_AGENT': 'My Desktop Browser',
        }
        middleware = MobileDetectionMiddleware()
        middleware.process_request(request)
        self.assertEqual(set_flavour.call_count, 0)


class SetFlavourMiddlewareTests(BaseTestCase):
    @patch('django_mobile.middleware.set_flavour')
    def test_set_flavour_through_get_parameter(self, set_flavour):
        request = Mock()
        request.GET = {'flavour': 'mobile'}
        middleware = SetFlavourMiddleware()
        middleware.process_request(request)
        self.assertEqual(set_flavour.call_args, (('mobile',), {'permanent': True}))
