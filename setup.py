from setuptools import setup, find_packages

install_requires = open('requirements.txt').read().split()

setup(
    name='mocurly',
    packages=find_packages(exclude=("tests", "tests.*")),
    package_data={'mocurly': ['templates/*.xml']},
    version='0.1',
    description='A library that allows your python tests to easily mock out the recurly library',
    author='Yoriyasu Yano',
    author_email='yoriy@captricity.com',
    url='https://github.com/Captricity/mocurly',
    download_url='https://github.com/Captricity/mocurly/tarball/v0.1',
    keywords = ['testing'],
    install_requires=install_requires,
    test_suite='tests'
)
