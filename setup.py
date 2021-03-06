from kdist import setup, cmdclasses, configure, parse_requirements, Nope

packages, data_files, package_dir = configure('src/python', 'colf')
version = __import__('colf').get_version()

# parse requirements.txt
requirements, dependency_links = parse_requirements('requirements.txt')

setup(
    name = "colf",
    version = version,
    url = 'http://pypi.k-tech.it/colf/',
    author = 'K-Tech',
    author_email = 'amministrazione@k-tech.it',
    description = '',
    data_files = data_files,
    package_dir = package_dir,
    packages = packages,
    cmdclass = cmdclasses,
    install_requires = requirements,
    dependency_links = dependency_links,
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
   ],
)
