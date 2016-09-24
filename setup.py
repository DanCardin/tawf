import os
from setuptools import setup


def read(file_name):
    cur_dir = os.path.dirname(__file__)
    path = os.path.join(cur_dir, file_name)
    return open(path).read()


setup(
    author='Dan Cardin',
    author_email='ddcardin@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
    ],
    description=(
        'Type Annotated Web framework emphasizing Dont Repeat Yourself'
    ),
    install_requires=['webob'],
    license='Apache2',
    long_description=read('README.rst'),
    name='tawdry',
    packages=['tawdry', 'tests'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    url='https://github.com/dancardin/tawdry',
    version='0.0.1',
)
