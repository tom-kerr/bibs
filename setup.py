from distutils.core import setup
import sys

major, minor = sys.version_info[0], sys.version_info[1]
version = 'python' + str(major) + '.' + str(minor)

setup(name='bibs',
      py_modules=['bibs'],
      requires=['yaml'],
      data_files=[('lib/'+ version +'/dist-packages/bibs/sources/', 
                   ['sources/openlibrary.yaml'])]
      )
