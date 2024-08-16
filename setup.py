from setuptools import setup
import re


def get_property(prop, project):
    result = re.search(r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format(prop),
                       open(f"{project}/__init__.py").read())
    return result.group(1)


project_name = 'lnremote'
setup(version=get_property('__version__', project_name), )
