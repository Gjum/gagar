try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='gagar',
      packages=['gagar'],
      py_modules=['gagar'],
      version='0.1.4',
      description='Standalone graphical agar.io Python client using GTK and agarnet',
      author='Gjum',
      author_email='code.gjum@gmail.com',
      url='https://github.com/Gjum/gagar',
      license='GPLv3',
      install_requires=[
          'agarnet >= 0.2.4',
          # TODO add gi, gobject, cairo requirements
      ],
      entry_points={'gui_scripts': ['gagar = gagar.main:main']},
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: X11 Applications :: GTK',
          'Intended Audience :: End Users/Desktop',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Natural Language :: English',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Topic :: Education',
          'Topic :: Games/Entertainment',
          'Topic :: Games/Entertainment :: Simulation',
      ],
)
