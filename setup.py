from distutils.core import setup

setup(name='bibs',
      author='Tom Kerr',
      author_email='thomkerr@gmail.com',
      url='https://github.com/reklaklislaw/bibs',
      description='An experimental python module with the goal of a shared syntax for querying RESTful Bibliographic APIs.',
      packages=['bibs'],
      package_dir={'bibs': 'src/bibs'},
      package_data={'bibs': ['sources/*.yaml']},
      requires=['lxml', 'yaml', 'xmltodict', 'dicttoxml'])
