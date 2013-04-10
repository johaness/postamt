from setuptools import setup

version = '0.1'
name = 'postamt'

setup(name=name,
      version=version,
      description="Email Message Creation & Sending",
      long_description="""
Light package that makes typical mail tasks easy:

 * Mail body both in plain text and HTML
 * Unicode in body and subject
 * Inline attachments (e.g. for HTML resources)
 * Attachments, with optional mime-type detection
      """,
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Programming Language :: Python',
          'Topic :: Communications :: Email',
          'Topic :: Internet',
          'License :: OSI Approved :: BSD License',
      ],
      py_modules=['postamt', ],
      license='BSD',
      keywords='',
      author='Johannes Steger, Kilian Klimek',
      author_email='jss@coders.de, kilian.klimek@gmail.com',
      url='https://github.com/johaness/postamt',
      zip_safe=True,
      install_requires=[
          'setuptools',
      ],
      )
