try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='gagar',
      packages=['gagar'],
      py_modules=['gagar'],
      version='0.1.0',
      description='Standalone graphical agar.io Python client using GTK',
      author='Gjum',
      author_email='code.gjum@gmail.com',
      url='https://github.com/Gjum/gagar',
      license='GPLv3',
      install_requires=[
          'agarnet >= 0.1.3',
          # TODO add gi, gobject, cairo requirements
      ],
      entry_points={'gui_scripts': ['gagar = gagar.main:main']},
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Environment :: X11 Applications :: GTK',
          'Intended Audience :: End Users/Desktop',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Natural Language :: English',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Topic :: Education',
          'Topic :: Games/Entertainment',
          'Topic :: Games/Entertainment :: Simulation',
      ],
)
