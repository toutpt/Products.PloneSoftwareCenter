"""
 View that provides the package index API
 for easy_install.

$Id:$
"""
import itertools
import os

from zope.interface import implements

from Products.Five import BrowserView
from Products.Five.traversable import FiveTraversable
from Products.CMFCore.utils import getToolByName

from Products.PloneSoftwareCenter.utils import get_projects_by_distutils_ids

from zope.publisher.interfaces.browser import IBrowserView
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.traversing.namespace import SimpleHandler
from zope.app.traversing.interfaces import TraversalError
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

class PyPISimpleTraverser(SimpleHandler):
    """ Custom traverser for the Simple Index
    """
    implements(IBrowserView)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def traverse(self, name, ignored):
        if name == '':
            return PyPISimpleView(self.context, self.request)
        path = name.split('/')
        if len(path) == 1:
            return PyPIProjectView(self.context, self.request, path[0])
        raise TraversalError(self.context, name)

SIMPLE = os.path.join(os.path.dirname(__file__), 'pypisimple.pt')
PROJECT = os.path.join(os.path.dirname(__file__), 'pypiproject.pt')
    
class PyPISimpleView(object):
    """view used for the main package index page"""
    implements(IBrowserPublisher)

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.sc = self.context
        self.catalog = getToolByName(self.context, 'portal_catalog')
        self.sc_path = '/'.join(self.sc.getPhysicalPath())

    def browserDefault(self, request):
        return self, ()

    def __of__(self, context):
        return self

    def __call__(self):
        template = ViewPageTemplateFile(SIMPLE)
        return template(self)

    def get_url_and_distutils_ids(self, brain):
        """returns url and title"""
        element = brain.getObject()
        yield {'distutilsMainId': element.distutilsMainId}

    def get_projects(self):
        """provides the simple view over the projects
        with links to the published files"""
        
        query = {'path': self.sc_path, 'portal_type': 'PSCProject',
                 'sort_on': 'getDistutilsMainId',
                 'review_state': 'published'}

        return itertools.chain(*[self.get_url_and_distutils_ids(brain)
                                 for brain in self.catalog(**query) ])

class PyPIProjectView(PyPISimpleView):

    def __init__(self, context, request, name):
        PyPISimpleView.__init__(self,  context, request)
        self.context = context
        self.request = request
        self.project_name = name
        self.projects = self._get_projects(name) 
        if self.projects == []:
            raise TraversalError(self.context, name)

    def _get_released_files(self, project):
        project_path = '/'.join(project.getPhysicalPath()) 
        query = {'path': project_path, 'portal_type': 'PSCRelease',
                 'review_state': ('alpha', 'beta', 'pre-release', 'final')}
        for brain in self.catalog(**query):
            for id_, file_ in brain.getObject().objectItems():
                yield {'url': file_.absolute_url(), 
                       'title': id_}

    def _get_projects(self, name):
        return get_projects_by_distutils_ids(self.context, [name])
       
    def __call__(self): 
        template = ViewPageTemplateFile(PROJECT)
        return template(self) 

    def get_name(self):
        return self.project_name

    def get_links(self):
        # let's browse the projects to get the releases
        # and the homepages
        links = []
        for project_name in self.projects:
            project = self.context[project_name]
            
            # archives first
            for archive in self._get_released_files(project):
                links.append(archive)           
            
            # then url links 
            fields = ('homepage', 'repository')
            for field in fields:
                value = getattr(project, field, u'')
                title = '%s %s' % (project_name, field)
                if value != u'':
                    links.append({'url': value, 'title': title,
                                  'rel': field})
            
        return links
